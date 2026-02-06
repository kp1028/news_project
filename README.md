# Django News Application

#  Project Description
This is a Django news application with three user roles:
- Reader
- Journalist
- Editor

Journalists can create articles and newsletters.  
Editors can review and approve content.  
Readers can view approved articles and subscribe to publishers or journalists.

Before starting make sure you have the following installed:
- Python 3.x
- pip
- Docker

# Setup Instructions
1. Clone repository
git clone <urURL>
cd  news_project

2. Install dependencies and create virtual environment.
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

3. Run migrations
python3 manage.py migrate
Run server: 
python3 manage.py runserver

4. Run with Docker
docker build -t news-project .
docker run -p 8000:8000 news-project

5. Open in browser:
http://localhost:8000

Some routes to access:
/register/  
Register as Reader, Journalist, or Editor.
 /publishers/  
View all publishers.
 /publishers/new/  
Create a publisher (Editor only).
