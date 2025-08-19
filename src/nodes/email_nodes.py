from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_openai import ChatOpenAI
from src.config import Config
from src.models import EmailType, CandidateInfo, ProjectInfo
from src.graphs.states import GraphState

class EmailProcessor:
    """邮件处理节点集合"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            api_key=Config.OPENAI_API_KEY
        )
        
    def classify_email(self, state: GraphState) -> GraphState:
        """邮件分类节点"""
        email = state["current_email"]
        
        classification_prompt = ChatPromptTemplate.from_template("""
        分析这封邮件并判断类型：
        
        邮件主题: {subject}
        邮件正文: {body}
        
        请判断是 CANDIDATE、PROJECT 还是 OTHER 类型。
        返回JSON格式：
        {{
            "type": "CANDIDATE|PROJECT|OTHER",
            "confidence": 0.85,
            "reason": "判断依据"
        }}
        """)
        
        chain = classification_prompt | self.llm | JsonOutputParser()
        
        try:
            result = chain.invoke({
                "subject": email.subject,
                "body": email.body[:500]
            })
            
            state["email_type"] = EmailType(result["type"])
            state["classification_confidence"] = result["confidence"]
            state["processing_log"].append(f"邮件分类: {result['type']}")
            
        except Exception as e:
            state["errors"].append(f"分类失败: {str(e)}")
            state["email_type"] = EmailType.OTHER
            
        return state
    
    # 问题：extract方法实现不完整
    def extract_candidate_info(self, state: GraphState) -> GraphState:
        # 需要完整实现：
        email = state["current_email"]
        
        extraction_prompt = ChatPromptTemplate.from_template("""...""")
        parser = PydanticOutputParser(pydantic_object=CandidateInfo)
        chain = extraction_prompt | self.llm | parser
        
        try:
            content = email.body
            if email.attachments:
                content += "\n\n附件内容:\n" + "\n".join(email.attachments)
            
            candidate = chain.invoke({"content": content})
            candidate.id = f"CAND_{email.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            state["candidate_info"] = candidate
            state["processing_log"].append(f"成功提取候选人信息: {candidate.name}")
        except Exception as e:
            state["errors"].append(f"候选人信息提取失败: {str(e)}")
        
        return state
    
    def extract_project_info(self, state: GraphState) -> GraphState:
        """提取项目信息"""
        # 简化实现
        email = state["current_email"]
        state["processing_log"].append("提取项目信息")
        return state