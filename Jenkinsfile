#!groovy​

pipeline {
    agent any
    stages {
         stage('Copy'){
             steps{
                 sh 'cp -r * /home/mannebot/mbot'
             }
        }
        stage('Setup'){
            steps {
                sh 'crontab -l > mycron'
                sh 'echo "@hourly python3 /home/mannebot/mbot/main.py" >> mycron'
                sh 'crontab mycron'
                sh 'rm mycron'
            }
        }
    }
}
