from datetime import date, datetime, timedelta

try:
    from google_calendar.calendar_service import GoogleCalendarService
    from google_calendar.calendar_freebusy import compute_free_slots
    from zoneinfo import ZoneInfo
    CALENDAR_AVAILABLE = True
except ImportError:
    GoogleCalendarService = None
    compute_free_slots = None
    ZoneInfo = None
    CALENDAR_AVAILABLE = False


def build_default_time_slots(duration_minutes: int = 60, all_day: bool = False) -> list[dict]:
    time_slots = []
    hour = 9
    if all_day:
        while hour < 20:
            start_dt = datetime.strptime(f"{hour:02d}:00", "%H:%M")
            end_dt = datetime.strptime("21:00", "%H:%M")
            time_slots.append(
                {"start_time": start_dt.time(), "end_time": end_dt.time(), "is_available": True}
            )
            hour += 1
        return time_slots

    slot_minutes = max(60, int(duration_minutes or 60))
    while hour < 21:
        start_dt = datetime.strptime(f"{hour:02d}:00", "%H:%M")
        end_dt = start_dt + timedelta(minutes=slot_minutes)
        if end_dt.hour > 21 or (end_dt.hour == 21 and end_dt.minute > 0):
            break
        time_slots.append(
            {"start_time": start_dt.time(), "end_time": end_dt.time(), "is_available": True}
        )
        hour += 1
    return time_slots


async def get_time_slots_for_date(
    target_date: date,
    service_id: int,
    service_name: str | None,
    duration_minutes: int = 60,
    all_day: bool = False,
) -> tuple[list[dict], bool, str | None]:
    if CALENDAR_AVAILABLE and GoogleCalendarService:
        try:
            calendar_service = GoogleCalendarService()
            work_start = datetime.strptime("09:00", "%H:%M").time()
            work_end = datetime.strptime("21:00", "%H:%M").time()
            day_start = datetime.combine(target_date, work_start)
            day_end = datetime.combine(target_date, work_end)
            events = await calendar_service.list_events(day_start, day_end)

            service_tag = f"Service ID: {service_id}"
            extra_service_tag = "Service ID: 9"
            busy = []
            busy_extra = []
            for event in events:
                desc = event.get("description") or ""
                summary = event.get("summary") or ""
                start = event.get("start")
                end = event.get("end")
                if not start or not end:
                    continue
                if start.tzinfo is None:
                    start = start.replace(tzinfo=ZoneInfo(calendar_service.time_zone))
                if end.tzinfo is None:
                    end = end.replace(tzinfo=ZoneInfo(calendar_service.time_zone))

                if extra_service_tag in desc:
                    busy_extra.append((start, end))
                    continue
                if (service_tag in desc) or (service_name and service_name in summary):
                    busy.append((start, end))

            tz = ZoneInfo(calendar_service.time_zone)
            day_start = datetime.combine(target_date, work_start, tzinfo=tz)
            day_end = datetime.combine(target_date, work_end, tzinfo=tz)
            slot_minutes = max(60, int(duration_minutes or 60))
            step_minutes = 60
            min_slot_minutes = 60

            def _overlap_count(start: datetime, end: datetime, intervals: list[tuple[datetime, datetime]]) -> int:
                count = 0
                for b_start, b_end in intervals:
                    if start < b_end and end > b_start:
                        count += 1
                return count

            def _generate_slots():
                slots = []
                cursor = day_start
                while cursor + timedelta(minutes=min_slot_minutes) <= day_end:
                    slot_end = day_end if all_day else cursor + timedelta(minutes=slot_minutes)
                    slots.append((cursor, slot_end))
                    cursor += timedelta(minutes=step_minutes)
                return slots

            if service_id == 9:
                slots = []
                for slot_start, slot_end in _generate_slots():
                    if _overlap_count(slot_start, slot_end, busy) < 2:
                        slots.append(
                            {"start_time": slot_start.time(), "end_time": slot_end.time(), "is_available": True}
                        )
                return slots, True, None

            def _extra_available(slot_start: datetime) -> bool:
                pre_start = slot_start - timedelta(hours=1)
                pre_end = slot_start
                if pre_start < day_start:
                    return True
                return _overlap_count(pre_start, pre_end, busy_extra) < 2

            filtered = []
            if all_day:
                for slot_start, slot_end in _generate_slots():
                    if _overlap_count(slot_start, slot_end, busy) > 0:
                        continue
                    if _extra_available(slot_start):
                        filtered.append(
                            {"start_time": slot_start.time(), "end_time": slot_end.time(), "is_available": True}
                        )
            else:
                slots = compute_free_slots(
                    busy,
                    day_start,
                    day_end,
                    slot_minutes=slot_minutes,
                    step_minutes=step_minutes,
                )
                for slot_start, slot_end in slots:
                    if _extra_available(slot_start):
                        filtered.append(
                            {"start_time": slot_start.time(), "end_time": slot_end.time(), "is_available": True}
                        )
            return filtered, True, None
        except Exception as e:
            return build_default_time_slots(duration_minutes, all_day=all_day), False, str(e)

    return build_default_time_slots(duration_minutes, all_day=all_day), False, None


async def is_booking_available(
    target_date: date,
    start_time: datetime,
    duration_minutes: int,
    service_id: int,
    service_name: str | None,
) -> tuple[bool, str | None]:
    if not (CALENDAR_AVAILABLE and GoogleCalendarService):
        return True, None

    try:
        calendar_service = GoogleCalendarService()
        tz = ZoneInfo(calendar_service.time_zone)
        work_start = datetime.strptime("09:00", "%H:%M").time()
        work_end = datetime.strptime("21:00", "%H:%M").time()
        day_start = datetime.combine(target_date, work_start, tzinfo=tz)
        day_end = datetime.combine(target_date, work_end, tzinfo=tz)
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=tz)
        events = await calendar_service.list_events(day_start, day_end)

        service_tag = f"Service ID: {service_id}"
        extra_service_tag = "Service ID: 9"
        busy = []
        busy_extra = []
        for event in events:
            desc = event.get("description") or ""
            summary = event.get("summary") or ""
            start = event.get("start")
            end = event.get("end")
            if not start or not end:
                continue
            if start.tzinfo is None:
                start = start.replace(tzinfo=ZoneInfo(calendar_service.time_zone))
            if end.tzinfo is None:
                end = end.replace(tzinfo=ZoneInfo(calendar_service.time_zone))

            if extra_service_tag in desc:
                busy_extra.append((start, end))
                continue
            if (service_tag in desc) or (service_name and service_name in summary):
                busy.append((start, end))

        def _overlap_count(start: datetime, end: datetime, intervals: list[tuple[datetime, datetime]]) -> int:
            count = 0
            for b_start, b_end in intervals:
                if start < b_end and end > b_start:
                    count += 1
            return count

        end_time = start_time + timedelta(minutes=duration_minutes)
        if start_time < day_start or end_time > day_end:
            return False, "Выбранный интервал выходит за пределы рабочего времени."

        if service_id == 9:
            if _overlap_count(start_time, end_time, busy) >= 2:
                return False, "Выбранное время пересекается с двумя бронированиями этой услуги."
            return True, None

        if _overlap_count(start_time, end_time, busy) > 0:
            return False, "Выбранное время пересекается с другой бронью этой услуги."

        pre_start = start_time - timedelta(hours=1)
        pre_end = start_time
        if pre_start < day_start:
            return True, None
        if _overlap_count(pre_start, pre_end, busy_extra) >= 2:
            return False, "За час до начала занято обеими бронями доп. услуги."

        return True, None
    except Exception:
        return True, None

