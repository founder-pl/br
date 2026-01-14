"""
LLM Service Integration for B+R Documentation.
"""
import os
from typing import Dict, Any, List
import httpx
import structlog

from .prompts import BR_EXPENSE_DOC_PROMPT, LLM_REFINEMENT_PROMPT

logger = structlog.get_logger(__name__)


async def generate_with_llm(prompt: str, llm_service_url: str) -> str:
    """Generate documentation using LLM service."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{llm_service_url}/v1/chat/completions",
            json={
                "model": "default",
                "messages": [
                    {"role": "system", "content": BR_EXPENSE_DOC_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            raise Exception(f"LLM service error: {response.status_code}")


async def refine_with_llm(
    content: str,
    validation_issues: List[Dict[str, Any]],
    max_iterations: int = 3
) -> Dict[str, Any]:
    """
    Stage 6: Iterative Refinement - Use LLM to fix validation issues.
    
    Args:
        content: Original document content
        validation_issues: List of issues from validation
        max_iterations: Maximum refinement attempts
        
    Returns:
        Dict with refined content and refinement log
    """
    if not validation_issues:
        return {"status": "no_changes", "content": content, "iterations": 0}
    
    # Format issues for LLM
    issues_text = "\n".join([
        f"- [{i.get('severity', 'warning').upper()}] {i.get('message', '')}"
        f"\n  Lokalizacja: {i.get('location', 'unknown')}"
        f"\n  Sugestia: {i.get('suggestion', '')}"
        for i in validation_issues
    ])
    
    refined_content = content
    refinement_log = []
    
    for iteration in range(max_iterations):
        try:
            # Call LLM for refinement
            prompt = LLM_REFINEMENT_PROMPT.format(
                issues=issues_text,
                document=refined_content
            )
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Try OpenRouter first
                api_key = os.environ.get('OPENROUTER_API_KEY')
                if api_key:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "HTTP-Referer": "https://br-system.local",
                            "X-Title": "BR Documentation Refiner"
                        },
                        json={
                            "model": os.environ.get('OPENROUTER_MODEL', 'google/gemma-2-9b-it:free'),
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.3,
                            "max_tokens": 8000
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        new_content = result['choices'][0]['message']['content']
                        
                        # Validate that we got markdown back
                        if new_content and '#' in new_content:
                            refined_content = new_content
                            refinement_log.append({
                                "iteration": iteration + 1,
                                "status": "success",
                                "changes": "LLM refinement applied"
                            })
                            logger.info("LLM refinement applied", iteration=iteration+1)
                        else:
                            refinement_log.append({
                                "iteration": iteration + 1,
                                "status": "skipped",
                                "reason": "Invalid LLM response"
                            })
                    else:
                        refinement_log.append({
                            "iteration": iteration + 1,
                            "status": "failed",
                            "reason": f"API error: {response.status_code}"
                        })
                else:
                    # No API key, skip LLM refinement
                    refinement_log.append({
                        "iteration": iteration + 1,
                        "status": "skipped",
                        "reason": "No OPENROUTER_API_KEY configured"
                    })
                    break
                    
        except Exception as e:
            logger.warning("LLM refinement failed", iteration=iteration+1, error=str(e))
            refinement_log.append({
                "iteration": iteration + 1,
                "status": "error",
                "reason": str(e)
            })
    
    return {
        "status": "refined" if refinement_log else "no_changes",
        "content": refined_content,
        "iterations": len(refinement_log),
        "log": refinement_log
    }
