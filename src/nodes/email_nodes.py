from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_openai import ChatOpenAI
from src.config import Config
from src.models import EmailType, CandidateInfo, ProjectInfo
from src.graphs.states import GraphState

class EmailProcessor:
    """Email processing node collection"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            api_key=Config.OPENAI_API_KEY
        )
        
    def classify_email(self, state: GraphState) -> GraphState:
        """Email classification node"""
        email = state["current_email"]
        
        classification_prompt = ChatPromptTemplate.from_template("""
        Analyze this email and determine its type:
        
        Email Subject: {subject}
        Email Body: {body}
        
        Please determine if it's CANDIDATE, PROJECT, or OTHER type.
        Return in JSON format:
        {{
            "type": "CANDIDATE|PROJECT|OTHER",
            "confidence": 0.85,
            "reason": "reasoning basis"
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
            state["processing_log"].append(f"Email classification: {result['type']}")
            
        except Exception as e:
            state["errors"].append(f"Classification failed: {str(e)}")
            state["email_type"] = EmailType.OTHER
            
        return state
    
    def extract_candidate_info(self, state: GraphState) -> GraphState:
        """Extract candidate information"""
        email = state["current_email"]
        
        extraction_prompt = ChatPromptTemplate.from_template("""
        Extract candidate information from the following resume content, please return strictly in JSON format:
        
        Content: {content}
        
        Please extract the following information and return in JSON format:
        {{
            "name": "candidate full name",
            "title": "professional title or desired position",
            "experience_years": "years of work experience (number + years, e.g. '5 years')",
            "skills": "technical skills list, separated by commas",
            "certificates": "certification information, separated by commas",
            "education": "educational background",
            "location_preference": "work location preference",
            "expected_salary": "expected salary range",
            "contact": "contact information (email, phone, etc.)"
        }}
        
        If some information is not found, please use empty strings.
        """)
        
        parser = PydanticOutputParser(pydantic_object=CandidateInfo)
        chain = extraction_prompt | self.llm | parser
        
        try:
            content = email.body
            if email.attachments:
                content += "\n\nAttachment content:\n" + "\n".join(email.attachments)
            
            candidate = chain.invoke({"content": content[:2000]})  # Limit content length
            candidate.id = f"CAND_{email.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            state["candidate_info"] = candidate
            state["processing_log"].append(f"Successfully extracted candidate information: {candidate.name}")
            
        except Exception as e:
            state["errors"].append(f"Candidate information extraction failed: {str(e)}")
            # Create fallback candidate info
            state["candidate_info"] = CandidateInfo(
                id=f"CAND_{email.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                name="Unknown candidate",
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
        """Extract project information"""
        email = state["current_email"]
        
        extraction_prompt = ChatPromptTemplate.from_template("""
        Extract project information from the following project requirements content, please return strictly in JSON format:
        
        Content: {content}
        
        Please extract the following information and return in JSON format:
        {{
            "title": "project title or name",
            "type": "project type (e.g.: web development, mobile app, data analysis, etc.)",
            "tech_requirements": "technical requirements and tech stack, separated by commas",
            "description": "detailed project description",
            "budget": "project budget range",
            "duration": "project duration or timeline",
            "start_time": "project start time",
            "work_style": "work style (e.g.: remote, on-site, hybrid, etc.)"
        }}
        
        If some information is not found, please use empty strings.
        """)
        
        parser = PydanticOutputParser(pydantic_object=ProjectInfo)
        chain = extraction_prompt | self.llm | parser
        
        try:
            content = email.body
            if email.attachments:
                content += "\n\nAttachment content:\n" + "\n".join(email.attachments)
            
            project = chain.invoke({"content": content[:2000]})  # Limit content length
            project.id = f"PROJ_{email.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            state["project_info"] = project
            state["processing_log"].append(f"Successfully extracted project information: {project.title}")
            
        except Exception as e:
            state["errors"].append(f"Project information extraction failed: {str(e)}")
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