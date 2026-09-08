pipeline {
    agent any

    environment {
        IMAGE_NAME = 'notas-api'
        IMAGE_TAG = ''
    }

    stages {
        stage('Información de rama') {
            steps {
                script {
                    def safeBranch = env.BRANCH_NAME
                        .toLowerCase()
                        .replaceAll('[^a-z0-9_.-]', '-')

                    env.IMAGE_TAG = "${safeBranch}-${env.BUILD_NUMBER}"

                    echo "Rama: ${env.BRANCH_NAME}"
                    echo "Commit: ${env.GIT_COMMIT}"
                    echo "Imagen: ${env.IMAGE_NAME}:${env.IMAGE_TAG}"
                }
            }
        }

        stage('Preparar entorno') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python3 -m venv .venv'
                        sh '.venv/bin/python -m pip install --upgrade pip'
                        sh '.venv/bin/python -m pip install -r requirements-dev.txt'
                    } else {
                        bat 'python -m venv .venv'
                        bat '.venv\\Scripts\\python.exe -m pip install --upgrade pip'
                        bat '.venv\\Scripts\\python.exe -m pip install -r requirements-dev.txt'
                    }
                }
            }
        }

        stage('Tests unitarios') {
            steps {
                script {
                    if (isUnix()) {
                        sh '.venv/bin/python -m pytest --junitxml=test-results/junit.xml'
                    } else {
                        bat '.venv\\Scripts\\python.exe -m pytest --junitxml=test-results\\junit.xml'
                    }
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/junit.xml'
                }
            }
        }

        stage('Build imagen Docker') {
            steps {
                script {
                    if (isUnix()) {
                        sh "docker build -t ${env.IMAGE_NAME}:${env.IMAGE_TAG} ."
                    } else {
                        bat "docker build -t ${env.IMAGE_NAME}:${env.IMAGE_TAG} ."
                    }
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline exitoso. Imagen creada: ${env.IMAGE_NAME}:${env.IMAGE_TAG}"
        }
        failure {
            echo 'El pipeline falló; revisá la etapa y los resultados de pytest.'
        }
    }
}
