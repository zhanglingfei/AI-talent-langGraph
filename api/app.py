from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.main import TalentMatchingSystem

app = FastAPI(title="Talent Matching API")
system = TalentMatchingSystem()

class ProcessEmailRequest(BaseModel):
    label: Optional[str] = "all"

class MatchRequest(BaseModel):
    match_type: str  # "project_to_resume" or "resume_to_project"
    query_id: str

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/process-emails")
async def process_emails(request: ProcessEmailRequest):
    try:
        result = system.process_emails(request.label)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/match")
async def match(request: MatchRequest):
    try:
        if request.match_type == "project_to_resume":
            result = system.match_project_with_candidates(request.query_id)
        else:
            result = system.match_candidate_with_projects(request.query_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)