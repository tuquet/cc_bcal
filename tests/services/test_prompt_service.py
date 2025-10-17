from app.models.prompt import Prompt
from app.services import prompt_service
from app import db


class TestPromptService:

    def test_save_prompt_creates_and_returns_prompt(self, app):
        with app.app_context():
            # Arrange
            name = 'example.md'
            content = 'Hello world'

            # Act
            prompt = prompt_service.save_prompt(name, content)

            # Assert
            assert prompt.id is not None
            assert prompt.name == name
            assert prompt.content == content

    def test_save_prompt_invalid_name_raises(self, app):
        with app.app_context():
            try:
                prompt_service.save_prompt('badname', 'x')
                raised = False
            except ValueError:
                raised = True

            assert raised

    def test_get_all_prompts_returns_dict(self, app):
        with app.app_context():
            # Ensure table empty
            # Add two prompts
            p1 = Prompt(name='a.md', content='A')
            p2 = Prompt(name='b.md', content='B')
            db.session.add_all([p1, p2])
            db.session.commit()

            res = prompt_service.get_all_prompts()
            assert isinstance(res, dict)
            assert 'a.md' in res and res['a.md'] == 'A'
            assert 'b.md' in res and res['b.md'] == 'B'

    def test_delete_prompt_by_id(self, app):
        with app.app_context():
            p = Prompt(name='todelete.md', content='bye')
            db.session.add(p)
            db.session.commit()
            pid = p.id

            resp = prompt_service.delete_prompt_by_id(pid)
            # delete returns a Flask response tuple for success
            # For our usage check that prompt no longer exists
            assert db.session.get(Prompt, pid) is None

    def test_delete_prompt_not_found_returns_404(self, app):
        with app.app_context():
            resp, status = prompt_service.delete_prompt_by_id(999999)
            assert status == 404