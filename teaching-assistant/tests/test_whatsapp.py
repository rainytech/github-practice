import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import whatsapp as wa  # noqa: E402
from storage import Store  # noqa: E402

FRI = date(2026, 9, 25)


def test_message_matches_example():
    msg = wa.build_message(FRI, "17:30", "T.S. Grewal", "3.1", "Question 24", today=FRI)
    assert msg == "Class at 5:30 PM — T.S. Grewal, Page 3.1, Question No. 24. For assistance: 9567902805."


def test_message_other_day_and_missing_parts():
    sat = date(2026, 9, 26)
    assert wa.build_message(sat, "18:30", "", "", "pro-rata to start", today=FRI) == \
        "Class on Sat 26 Sep at 6:30 PM — pro-rata to start. For assistance: 9567902805."
    assert wa.build_message(None, None, "", "", "", today=FRI) == "Next class. For assistance: 9567902805."


def test_question_label():
    assert wa.question_label("Question 24") == "Question No. 24"
    assert wa.question_label("Illustration 13") == "Illustration No. 13"
    assert wa.question_label("Q No. 5") == "Q No. 5"
    assert wa.question_label("Question No. 24") == "Question No. 24"


def test_phone_and_url():
    assert wa.normalize_phone("95679 02805") == "919567902805"
    assert wa.normalize_phone("+91 95679-02805") == "919567902805"
    assert wa.normalize_phone("09567902805") == "919567902805"
    assert wa.whatsapp_url("9567902805", "Hi there") == "whatsapp://send?phone=919567902805&text=Hi%20there"
    assert wa.whatsapp_url("", "Hi") == "whatsapp://send?text=Hi"


def test_next_class():
    rows = [("2026-09-25", "18:30"), ("2026-09-26", "18:30")]
    assert wa.next_class(rows, datetime(2026, 9, 25, 12, 0)) == (FRI, "18:30")
    assert wa.next_class(rows, datetime(2026, 9, 25, 19, 10)) == (FRI, "18:30")  # running
    assert wa.next_class(rows, datetime(2026, 9, 25, 20, 0)) == (date(2026, 9, 26), "18:30")
    assert wa.next_class(rows, datetime(2026, 9, 27, 8, 0)) is None


def test_contact_saved_and_migration(tmp_path):
    s = Store(tmp_path)
    sid = s.student_id("Thomas")
    s.update_contact(sid, "95679 02805", "T.S. Grewal", "3.1")
    s2 = Store(tmp_path)  # reopen: migration runs again safely
    row = s2.student(sid)
    assert (row["phone"], row["book"], row["book_page"]) == ("95679 02805", "T.S. Grewal", "3.1")
    s2.set_schedule([("2026-09-25", "18:30", "Thomas")])
    assert s2.schedule_of(sid, "2026-09-25") == [("2026-09-25", "18:30")]
