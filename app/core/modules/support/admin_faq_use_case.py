from __future__ import annotations


async def get_admin_faq_entry(faq_repo, faq_id: int):
    return await faq_repo.get_by_id(faq_id)


async def toggle_admin_faq_active(faq_repo, faq_id: int):
    entry = await faq_repo.get_by_id(faq_id)
    if not entry:
        return None

    await faq_repo.set_active(faq_id, not entry.is_active)
    return await faq_repo.get_by_id(faq_id)


async def delete_admin_faq_entry(faq_repo, faq_id: int) -> None:
    await faq_repo.delete(faq_id)


async def create_admin_faq_entry(faq_repo, *, question: str, answer: str) -> int:
    return await faq_repo.add(question=question, answer=answer)


async def update_admin_faq_question(faq_repo, *, faq_id: int, question: str):
    await faq_repo.update_question(faq_id, question)
    return await faq_repo.get_by_id(faq_id)


async def update_admin_faq_answer(faq_repo, *, faq_id: int, answer: str):
    await faq_repo.update_answer(faq_id, answer)
    return await faq_repo.get_by_id(faq_id)
