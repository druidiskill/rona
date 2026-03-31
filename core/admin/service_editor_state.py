from __future__ import annotations

from aiogram.fsm.context import FSMContext


async def update_nested_state_data(
    state: FSMContext,
    root_key: str,
    updates: dict,
    *,
    field_name: str | None = None,
    field_value=None,
) -> dict:
    data = await state.get_data()
    nested = dict(data.get(root_key, {}))
    if updates:
        nested.update(updates)
    if field_name is not None:
        nested[field_name] = field_value
    await state.update_data({root_key: nested})
    return nested
