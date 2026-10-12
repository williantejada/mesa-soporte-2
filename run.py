from app import create_app
from app.cli import init_db, create_admin
app = create_app()
app.cli.add_command(init_db)
app.cli.add_command(create_admin)
if __name__ == "__main__":
    app.run(debug=False)
