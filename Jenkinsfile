pipeline {
    agent none 
    stages {
        stage('Build') { 
            agent {
                docker {
                    image 'python:3.11.7-alpine3.19' 
                }
            }
            steps {
                sh 'pip install -r requirements.txt'
                sh 'pyinstaller -F -i app.ico .\translator_deepl.py' 
                stash(name: 'compiled-results', includes: 'sources/*.py*') 
            }
        }
    }
}
