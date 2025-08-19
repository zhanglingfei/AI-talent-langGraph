from enum import Enum
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class EmailType(str, Enum):
    """邮件类型枚举"""
    CANDIDATE = "candidate"
    PROJECT = "project"
    OTHER = "other"

class EmailInfo(BaseModel):
    """邮件信息"""
    id: str
    subject: str
    body: str
    attachments: List[str] = []
    timestamp: datetime
    sender: str
    has_attachment: bool = False
    label_type: Optional[EmailType] = None

class CandidateInfo(BaseModel):
    """候选人信息"""
    id: str
    name: str = Field(description="候选人全名")
    title: str = Field(description="职业头衔")
    experience_years: str = Field(description="工作经验年限")
    skills: str = Field(description="技术技能")
    certificates: str = Field(default="", description="证书")
    education: str = Field(default="", description="教育背景")
    location_preference: str = Field(default="", description="工作地点偏好")
    expected_salary: str = Field(default="", description="期望薪资")
    contact: str = Field(default="", description="联系方式")

class ProjectInfo(BaseModel):
    """项目信息"""
    id: str
    title: str = Field(description="项目标题")
    type: str = Field(default="", description="项目类型")
    tech_requirements: str = Field(description="技术要求")
    description: str = Field(description="项目描述")
    budget: str = Field(default="", description="预算范围")
    duration: str = Field(default="", description="项目周期")
    start_time: str = Field(default="", description="开始时间")
    work_style: str = Field(default="", description="工作方式")

class MatchResult(BaseModel):
    """匹配结果"""
    id: str
    name: str
    score: int = Field(ge=0, le=100)
    reason: str