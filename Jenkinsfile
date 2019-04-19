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
                sh 'croncondition=$(crontab -l | grep -c mbot)'
                sh 'if [[ $croncondition -gt 0 ]] ; then echo "@hourly python3 /home/mannebot/mbot/main.py" >> mycron; fi'
                sh 'crontab mycron'
                sh 'rm mycron'
            }
        }
        stage('Start'){
            steps {
                sh ''
                // sh 'python3 /home/mannebot/mbot/main.py'
            }
        }
    }
}
