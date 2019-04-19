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
                sh 'cjob="$(crontab -l | grep -c \'mbot\')"'
                sh 'crontab -l | { cat; if [[ $cjob -gt 0 ]]; then echo "@hourly python3 /home/mannebot/mbot/main.py"; fi; } | crontab -;'
            }
        }
    }
}
