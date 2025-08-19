"""
Gmail服务集成
"""

import base64
from typing import List, Dict, Optional
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.config import Config
from src.models import EmailInfo

class GmailService:
    """Gmail服务类"""
    
    def __init__(self):
        self.service = None
        self._initialize_service()
    
    # 问题：认证未实现，需要添加：
    def _initialize_service(self):
        try:
            # 需要实现OAuth2认证
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
            import pickle
            import os
            
            SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
            creds = None
            
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        Config.CREDENTIALS_PATH, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
            
            self.service = build('gmail', 'v1', credentials=creds)
        except Exception as e:
            print(f"Gmail服务初始化失败: {e}")
    
    def list_messages(self, query: str = "", max_results: int = 10) -> List[Dict]:
        """列出邮件"""
        if not self.service:
            return []
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            return messages
        except Exception as e:
            print(f"获取邮件列表失败: {e}")
            return []
    
    def get_message(self, msg_id: str) -> Optional[EmailInfo]:
        """获取邮件详情"""
        if not self.service:
            return None
        
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id
            ).execute()
            
            # 解析邮件内容
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            
            # 获取邮件正文
            body = self._get_message_body(message['payload'])
            
            # 获取附件
            attachments = self._get_attachments(message['payload'])
            
            return EmailInfo(
                id=msg_id,
                subject=subject,
                body=body,
                sender=sender,
                attachments=attachments,
                has_attachment=len(attachments) > 0,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"获取邮件详情失败: {e}")
            return None
    
    def _get_message_body(self, payload: Dict) -> str:
        """提取邮件正文"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        elif payload['body'].get('data'):
            body = base64.urlsafe_b64decode(
                payload['body']['data']
            ).decode('utf-8')
        
        return body
    
    def _get_attachments(self, payload: Dict) -> List[str]:
        """获取附件列表"""
        attachments = []
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('filename'):
                    attachments.append(part['filename'])
        
        return attachments