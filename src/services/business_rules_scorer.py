"""
业务规则评分器
实现基于硬性条件和业务规则的匹配评分
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from src.models import CandidateInfo, ProjectInfo
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class BusinessRulesScorer:
    """业务规则评分器"""
    
    def __init__(self):
        # 技能关键词映射
        self.skill_keywords = {
            "java": ["java", "spring", "springboot", "maven", "gradle"],
            "python": ["python", "django", "flask", "fastapi", "pandas", "numpy"],
            "javascript": ["javascript", "js", "node", "nodejs", "react", "vue", "angular"],
            "web": ["html", "css", "frontend", "backend", "fullstack", "web开发"],
            "database": ["mysql", "postgresql", "mongodb", "redis", "sql", "数据库"],
            "cloud": ["aws", "azure", "kubernetes", "docker", "云计算", "微服务"],
            "ai": ["机器学习", "深度学习", "tensorflow", "pytorch", "nlp", "cv", "人工智能"]
        }
        
        # 经验年限解析
        self.experience_patterns = {
            r"(\d+)\s*年": r"\1",
            r"(\d+)\s*-\s*(\d+)\s*年": r"\2",  # 取上限
            r"(\d+)\s*以上": r"\1",
            r"senior|高级|资深": "5",
            r"junior|初级|新人": "1",
            r"mid|中级": "3"
        }
    
    def apply_hard_filters(self, candidates: List[Dict[str, Any]], project_requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """应用硬性条件过滤"""
        filtered_candidates = []
        
        for candidate in candidates:
            if self._passes_hard_filters(candidate, project_requirements):
                filtered_candidates.append(candidate)
        
        logger.info(f"硬条件过滤: {len(candidates)} → {len(filtered_candidates)}")
        return filtered_candidates
    
    def _passes_hard_filters(self, candidate: Dict[str, Any], requirements: Dict[str, Any]) -> bool:
        """检查候选人是否通过硬性条件"""
        
        # 1. 地点要求
        required_location = requirements.get("location", "").lower()
        candidate_location = candidate.get("location_preference", "").lower()
        
        if required_location and candidate_location:
            if not self._location_matches(candidate_location, required_location):
                logger.debug(f"地点不匹配: {candidate_location} vs {required_location}")
                return False
        
        # 2. 最低经验要求
        min_experience = requirements.get("min_experience_years")
        if min_experience:
            candidate_exp = self._extract_experience_years(candidate.get("experience_years", ""))
            if candidate_exp < min_experience:
                logger.debug(f"经验不足: {candidate_exp} < {min_experience}")
                return False
        
        # 3. 薪资范围
        budget_range = requirements.get("salary_range")
        candidate_salary = candidate.get("expected_salary", "")
        if budget_range and candidate_salary:
            if not self._salary_compatible(candidate_salary, budget_range):
                logger.debug(f"薪资不匹配: {candidate_salary} vs {budget_range}")
                return False
        
        # 4. 必需技能
        required_skills = requirements.get("required_skills", [])
        candidate_skills = candidate.get("skills", "").lower()
        for skill in required_skills:
            if not self._has_skill(candidate_skills, skill.lower()):
                logger.debug(f"缺少必需技能: {skill}")
                return False
        
        return True
    
    def calculate_business_score(self, candidate: Dict[str, Any], project: Dict[str, Any]) -> Tuple[int, str]:
        """计算业务规则评分"""
        total_score = 0
        score_breakdown = []
        
        # 1. 技能匹配评分 (0-40分)
        skill_score = self._calculate_skill_score(
            candidate.get("skills", ""),
            project.get("tech_requirements", "")
        )
        total_score += skill_score
        score_breakdown.append(f"技能匹配: {skill_score}/40")
        
        # 2. 经验匹配评分 (0-30分) 
        exp_score = self._calculate_experience_score(
            candidate.get("experience_years", ""),
            project.get("tech_requirements", "")
        )
        total_score += exp_score
        score_breakdown.append(f"经验匹配: {exp_score}/30")
        
        # 3. 其他因素评分 (0-30分)
        other_score = self._calculate_other_factors_score(candidate, project)
        total_score += other_score
        score_breakdown.append(f"其他因素: {other_score}/30")
        
        reason = f"业务规则评分 ({' | '.join(score_breakdown)})"
        return total_score, reason
    
    def _calculate_skill_score(self, candidate_skills: str, project_requirements: str) -> int:
        """计算技能匹配分数"""
        if not candidate_skills or not project_requirements:
            return 0
        
        candidate_skills = candidate_skills.lower()
        project_requirements = project_requirements.lower()
        
        total_matches = 0
        total_requirements = 0
        
        # 检查各技能类别的匹配度
        for category, keywords in self.skill_keywords.items():
            # 检查项目是否需要该技能类别
            category_required = any(keyword in project_requirements for keyword in keywords)
            if category_required:
                total_requirements += 1
                # 检查候选人是否具备该技能类别
                candidate_has_skill = any(keyword in candidate_skills for keyword in keywords)
                if candidate_has_skill:
                    total_matches += 1
        
        if total_requirements == 0:
            return 20  # 没有明确要求时给基础分
        
        # 计算匹配百分比并转换为40分制
        match_percentage = total_matches / total_requirements
        return min(40, int(match_percentage * 40))
    
    def _calculate_experience_score(self, candidate_exp: str, project_requirements: str) -> int:
        """计算经验匹配分数"""
        candidate_years = self._extract_experience_years(candidate_exp)
        
        # 从项目要求中提取经验要求
        required_years = self._extract_required_experience(project_requirements)
        
        if required_years == 0:
            return 15  # 没有明确要求时给基础分
        
        # 计算经验匹配度
        if candidate_years >= required_years:
            # 经验充足，根据超出程度给分
            if candidate_years >= required_years * 1.5:
                return 30  # 经验非常充足
            else:
                return 25  # 经验充足
        else:
            # 经验不足，按比例扣分
            ratio = candidate_years / required_years
            return max(0, int(ratio * 20))
    
    def _calculate_other_factors_score(self, candidate: Dict[str, Any], project: Dict[str, Any]) -> int:
        """计算其他因素分数"""
        score = 0
        
        # 工作方式匹配 (0-10分)
        project_work_style = project.get("work_style", "").lower()
        if "远程" in project_work_style or "remote" in project_work_style:
            score += 10  # 远程工作加分
        elif "现场" in project_work_style or "on-site" in project_work_style:
            score += 5   # 现场工作基础分
        
        # 教育背景 (0-10分)
        education = candidate.get("education", "").lower()
        if "硕士" in education or "master" in education:
            score += 10
        elif "本科" in education or "bachelor" in education:
            score += 8
        elif "大专" in education or "专科" in education:
            score += 6
        
        # 证书加分 (0-10分)
        certificates = candidate.get("certificates", "").lower()
        if certificates and certificates != "":
            # 根据证书内容给分
            if any(cert in certificates for cert in ["aws", "azure", "google cloud", "kubernetes"]):
                score += 10  # 云计算证书高分
            elif any(cert in certificates for cert in ["pmp", "scrum", "agile"]):
                score += 8   # 项目管理证书
            else:
                score += 5   # 其他证书基础分
        
        return min(30, score)  # 最高30分
    
    def _location_matches(self, candidate_location: str, required_location: str) -> bool:
        """检查地点是否匹配"""
        # 简单的字符串包含检查，可扩展为更复杂的地理位置匹配
        return required_location in candidate_location or candidate_location in required_location
    
    def _extract_experience_years(self, exp_text: str) -> int:
        """提取经验年限"""
        if not exp_text:
            return 0
        
        exp_text = exp_text.lower()
        
        for pattern, replacement in self.experience_patterns.items():
            match = re.search(pattern, exp_text)
            if match:
                try:
                    if replacement.startswith(r"\"):
                        # 使用正则替换
                        result = re.sub(pattern, replacement, exp_text)
                        return int(result)
                    else:
                        # 直接返回固定值
                        return int(replacement)
                except (ValueError, TypeError):
                    continue
        
        # 尝试直接提取数字
        numbers = re.findall(r'\d+', exp_text)
        if numbers:
            return int(numbers[0])
        
        return 0
    
    def _extract_required_experience(self, requirements: str) -> int:
        """从项目要求中提取经验要求"""
        if not requirements:
            return 0
        
        requirements = requirements.lower()
        
        # 查找经验要求模式
        patterns = [
            r"(\d+)\s*年以上",
            r"(\d+)\s*\+\s*年",
            r"minimum\s*(\d+)\s*year",
            r"至少\s*(\d+)\s*年"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, requirements)
            if match:
                return int(match.group(1))
        
        # 根据关键词推断
        if any(keyword in requirements for keyword in ["senior", "高级", "资深"]):
            return 5
        elif any(keyword in requirements for keyword in ["junior", "初级", "新人"]):
            return 1
        elif any(keyword in requirements for keyword in ["mid", "中级"]):
            return 3
        
        return 0
    
    def _salary_compatible(self, candidate_salary: str, budget_range: str) -> bool:
        """检查薪资是否兼容"""
        try:
            # 简化的薪资匹配逻辑
            candidate_min = self._extract_salary_min(candidate_salary)
            budget_max = self._extract_salary_max(budget_range)
            
            # 如果候选人期望薪资的最低值不超过预算的最高值，则兼容
            return candidate_min <= budget_max
        except:
            return True  # 解析失败时默认兼容
    
    def _extract_salary_min(self, salary_text: str) -> int:
        """提取薪资最小值(k为单位)"""
        numbers = re.findall(r'(\d+)k?', salary_text.lower())
        if numbers:
            return int(numbers[0])
        return 0
    
    def _extract_salary_max(self, salary_text: str) -> int:
        """提取薪资最大值(k为单位)"""
        numbers = re.findall(r'(\d+)k?', salary_text.lower())
        if numbers:
            return int(numbers[-1])  # 取最后一个数字作为上限
        return 999  # 如果无法解析，返回很大的值表示无上限
    
    def _has_skill(self, candidate_skills: str, required_skill: str) -> bool:
        """检查候选人是否具备特定技能"""
        # 检查技能关键词
        for category, keywords in self.skill_keywords.items():
            if required_skill in keywords:
                return any(keyword in candidate_skills for keyword in keywords)
        
        # 直接字符串匹配
        return required_skill in candidate_skills