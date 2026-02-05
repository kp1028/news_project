# Django News Application

## Project Description
This is a Django news application with three user roles:
- Reader
- Journalist
- Editor

Journalists can create articles and newsletters.  
Editors can review and approve content.  
Readers can view approved articles and subscribe to publishers or journalists.

## Setup Instructions

1. Install dependencies
pip install -r requirements.txt
Run migrations: python3 manage.py migrate
Run server: python3 manage.py runserver

Some routes to access:
/register/  
Register as Reader, Journalist, or Editor.
 /publishers/  
View all publishers.
 /publishers/new/  
Create a publisher (Editor only).
