from pathlib import Path
from streamlit.testing.v1 import AppTest

APP=Path(__file__).resolve().parents[1]/'app.py'

def test_hosted_access_fails_closed_without_password(monkeypatch):
    monkeypatch.setenv('RADAR_REQUIRE_AUTH','true')
    monkeypatch.delenv('RADAR_DASHBOARD_PASSWORD',raising=False)
    app=AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert any('not configured' in e.value for e in app.error)
    assert len(app.sidebar.radio)==0

def test_wrong_password_cannot_open_research(monkeypatch):
    monkeypatch.setenv('RADAR_REQUIRE_AUTH','true')
    monkeypatch.setenv('RADAR_DASHBOARD_PASSWORD','fixture-only-password')
    app=AppTest.from_file(str(APP)).run()
    app.text_input[0].set_value('wrong')
    app.button[0].click().run()
    assert not app.exception
    assert any('Incorrect password' in e.value for e in app.error)
    assert len(app.sidebar.radio)==0

def test_correct_password_opens_research_with_isolated_data(tmp_path,monkeypatch):
    from earnings_radar import config,db
    monkeypatch.setenv('RADAR_REQUIRE_AUTH','true')
    monkeypatch.setenv('RADAR_DASHBOARD_PASSWORD','fixture-only-password')
    monkeypatch.setenv('RADAR_RESEARCH_DB_PATH',str(tmp_path/'research.db'))
    monkeypatch.setattr(config,'DB_PATH',tmp_path/'app.db')
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'app.db')
    app=AppTest.from_file(str(APP)).run()
    app.text_input[0].set_value('fixture-only-password')
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state['_radar_access_granted']
    assert app.sidebar.radio[0].value=='Today'
