from datetime import datetime
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
    
    def extract_candidate_info(self, state: GraphState) -> GraphState:
        """提取候选人信息"""
        email = state["current_email"]
        
        extraction_prompt = ChatPromptTemplate.from_template("""
        从以下简历内容中提取候选人信息，请严格按照JSON格式返回：
        
        内容: {content}
        
        请提取以下信息并返回JSON格式：
        {{
            "name": "候选人全名",
            "title": "职业头衔或期望职位",
            "experience_years": "工作经验年限（数字+年，如'5年'）",
            "skills": "技术技能列表，用逗号分隔",
            "certificates": "证书信息，用逗号分隔",
            "education": "教育背景",
            "location_preference": "工作地点偏好",
            "expected_salary": "期望薪资范围",
            "contact": "联系方式（邮箱、电话等）"
        }}
        
        如果某些信息未找到，请使用空字符串。
        """)
        
        parser = PydanticOutputParser(pydantic_object=CandidateInfo)
        chain = extraction_prompt | self.llm | parser
        
        try:
            content = email.body
            if email.attachments:
                content += "\n\n附件内容:\n" + "\n".join(email.attachments)
            
            candidate = chain.invoke({"content": content[:2000]})  # Limit content length
            candidate.id = f"CAND_{email.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            state["candidate_info"] = candidate
            state["processing_log"].append(f"成功提取候选人信息: {candidate.name}")
            
        except Exception as e:
            state["errors"].append(f"候选人信息提取失败: {str(e)}")
            # Create fallback candidate info
            state["candidate_info"] = CandidateInfo(
                id=f"CAND_{email.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                name="未知候选人",
                title="",
                experience_years="",
                skills="",
                certificates="",
                education="",
                location_preference="",
                expected_salary="",
                contact=email.sender
            )
        
        return state
    
    def extract_project_info(self, state: GraphState) -> GraphState:
        """提取项目信息"""
        email = state["current_email"]
        
        extraction_prompt = ChatPromptTemplate.from_template("""
        从以下项目需求内容中提取项目信息，请严格按照JSON格式返回：
        
        内容: {content}
        
        请提取以下信息并返回JSON格式：
        {{
            "title": "项目标题或名称",
            "type": "项目类型（如：网站开发、移动应用、数据分析等）",
            "tech_requirements": "技术要求和技术栈，用逗号分隔",
            "description": "项目详细描述",
            "budget": "项目预算范围",
            "duration": "项目周期或时长",
            "start_time": "项目开始时间",
            "work_style": "工作方式（如：远程、现场、混合等）"
        }}
        
        如果某些信息未找到，请使用空字符串。
        """)
        
        parser = PydanticOutputParser(pydantic_object=ProjectInfo)
        chain = extraction_prompt | self.llm | parser
        
        try:
            content = email.body
            if email.attachments:
                content += "\n\n附件内容:\n" + "\n".join(email.attachments)
            
            project = chain.invoke({"content": content[:2000]})  # Limit content length
            project.id = f"PROJ_{email.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            state["project_info"] = project
            state["processing_log"].append(f"成功提取项目信息: {project.title}")
            
        except Exception as e:
            state["errors"].append(f"项目信息提取失败: {str(e)}")
            # Create fallback project info
            state["project_info"] = ProjectInfo(
                id=f"PROJ_{email.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                title=email.subject,
                type="",
                tech_requirements="",
                description=email.body[:200],
                budget="",
                duration="",
                start_time="",
                work_style=""
            )
        
        return state