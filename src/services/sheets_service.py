"""
Google Sheets服务集成
"""

from typing import List, Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.config import Config

class SheetsService:
    """Google Sheets服务类"""
    
    def __init__(self):
        self.service = None
        self.spreadsheet_id = Config.SPREADSHEET_ID
        self._initialize_service()
    
    def _initialize_service(self):
        """初始化Sheets服务"""
        try:
            # TODO: 实现OAuth2认证
            # creds = Credentials.from_authorized_user_file(
            #     Config.CREDENTIALS_PATH,
            #     ['https://www.googleapis.com/auth/spreadsheets']
            # )
            # self.service = build('sheets', 'v4', credentials=creds)
            pass
        except Exception as e:
            print(f"Sheets服务初始化失败: {e}")
    
    def read_sheet(self, sheet_name: str, range_name: str = "A:Z") -> List[List[Any]]:
        """读取工作表数据"""
        if not self.service:
            return []
        
        try:
            range_full = f"{sheet_name}!{range_name}"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_full
            ).execute()
            
            values = result.get('values', [])
            return values
            
        except Exception as e:
            print(f"读取工作表失败: {e}")
            return []
    
    def append_row(self, sheet_name: str, row_data: Dict[str, Any]) -> bool:
        """追加行数据"""
        if not self.service:
            return False
        
        try:
            # 将字典转换为列表
            values = [list(row_data.values())]
            
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:Z",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            return True
            
        except Exception as e:
            print(f"追加数据失败: {e}")
            return False
    
    def update_cell(self, sheet_name: str, cell: str, value: Any) -> bool:
        """更新单元格"""
        if not self.service:
            return False
        
        try:
            range_name = f"{sheet_name}!{cell}"
            body = {
                'values': [[value]]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            return True
            
        except Exception as e:
            print(f"更新单元格失败: {e}")
            return False
    
    def batch_update(self, sheet_name: str, start_cell: str, values: List[List[Any]]) -> bool:
        """批量更新数据"""
        if not self.service:
            return False
        
        try:
            range_name = f"{sheet_name}!{start_cell}"
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            return True
            
        except Exception as e:
            print(f"批量更新失败: {e}")
            return False
    
    def append_candidate_data(self, candidate_data: Dict[str, Any]) -> bool:
        """保存候选人数据到简历数据库"""
        try:
            sheet_name = Config.SHEET_NAMES["RESUME_DATABASE"]
            return self.append_row(sheet_name, candidate_data)
        except Exception as e:
            print(f"保存候选人数据失败: {e}")
            return False
    
    def append_project_data(self, project_data: Dict[str, Any]) -> bool:
        """保存项目数据"""
        try:
            sheet_name = Config.SHEET_NAMES["PROJECTS"]
            return self.append_row(sheet_name, project_data)
        except Exception as e:
            print(f"保存项目数据失败: {e}")
            return False
    
    def append_match_data(self, match_data: Dict[str, Any]) -> bool:
        """保存匹配结果数据"""
        try:
            sheet_name = Config.SHEET_NAMES["MATCHES"]
            return self.append_row(sheet_name, match_data)
        except Exception as e:
            print(f"保存匹配数据失败: {e}")
            return False
    
    def get_candidates(self, filter_criteria: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """获取候选人列表，支持筛选"""
        try:
            sheet_name = Config.SHEET_NAMES["RESUME_DATABASE"]
            data = self.read_sheet(sheet_name)
            
            if not data or len(data) < 2:  # 没有数据或只有标题行
                return []
            
            # 假设第一行是标题
            headers = data[0]
            candidates = []
            
            for row in data[1:]:
                if len(row) >= len(headers):
                    candidate = dict(zip(headers, row))
                    candidates.append(candidate)
            
            return candidates
            
        except Exception as e:
            print(f"获取候选人数据失败: {e}")
            return []
    
    def get_projects(self, filter_criteria: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """获取项目列表，支持筛选"""
        try:
            sheet_name = Config.SHEET_NAMES["PROJECTS"]
            data = self.read_sheet(sheet_name)
            
            if not data or len(data) < 2:  # 没有数据或只有标题行
                return []
            
            # 假设第一行是标题
            headers = data[0]
            projects = []
            
            for row in data[1:]:
                if len(row) >= len(headers):
                    project = dict(zip(headers, row))
                    projects.append(project)
            
            return projects
            
        except Exception as e:
            print(f"获取项目数据失败: {e}")
            return []