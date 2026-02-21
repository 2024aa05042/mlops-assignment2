// Jenkinsfile for Cats vs Dogs API CI/CD Pipeline
// Place this file in repository root: ./Jenkinsfile

pipeline {
    agent any
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }
    
    parameters {
        string(name: 'DOCKER_REGISTRY', defaultValue: 'ghcr.io', description: 'Docker registry URL')
        string(name: 'IMAGE_TAG', defaultValue: 'latest', description: 'Docker image tag')
        booleanParam(name: 'DEPLOY', defaultValue: false, description: 'Deploy to Kubernetes after build?')
    }
    
    environment {
        DOCKER_REGISTRY = "${params.DOCKER_REGISTRY}"
        IMAGE_NAME = "${DOCKER_REGISTRY}/${GITHUB_ORG}/cats-dogs"
        IMAGE_TAG = "${params.IMAGE_TAG}"
        GIT_COMMIT_SHORT = "${GIT_COMMIT.take(8)}"
        KUBECONFIG = credentials('kubeconfig-prod')
    }
    
    stages {
        stage('Checkout') {
            steps {
                script {
                    echo "🔄 Checking out code..."
                    checkout scm
                }
            }
        }
        
        stage('Setup') {
            steps {
                script {
                    echo "📦 Setting up environment..."
                    sh '''
                        python --version
                        pip install --upgrade pip
                        pip install -r requirements.txt
                    '''
                }
            }
        }
        
        stage('Test') {
            steps {
                script {
                    echo "🧪 Running tests..."
                    sh '''
                        python -m pytest tests/ \
                            --junitxml=reports/junit.xml \
                            --cov=src --cov-report=xml \
                            --cov-report=html:reports/coverage_html
                    '''
                }
                junit 'reports/junit.xml'
                publishHTML([
                    reportDir: 'reports/coverage_html',
                    reportFiles: 'index.html',
                    reportName: 'Code Coverage'
                ])
            }
        }
        
        stage('Lint') {
            steps {
                script {
                    echo "🔍 Linting code..."
                    sh '''
                        python -m flake8 src/ --max-line-length=100 --count || true
                    '''
                }
            }
        }
        
        stage('Build') {
            steps {
                script {
                    echo "🔨 Building Docker image..."
                    sh '''
                        docker build \
                            -t ${IMAGE_NAME}:${IMAGE_TAG} \
                            -t ${IMAGE_NAME}:${GIT_COMMIT_SHORT} \
                            -f Dockerfile.api .
                    '''
                }
            }
        }
        
        stage('Push to Registry') {
            when {
                branch 'main'
            }
            steps {
                script {
                    echo "📤 Pushing image to registry..."
                    withCredentials([
                        usernamePassword(
                            credentialsId: 'github-container-registry',
                            usernameVariable: 'GHCR_USER',
                            passwordVariable: 'GHCR_PASS'
                        )
                    ]) {
                        sh '''
                            echo ${GHCR_PASS} | docker login ghcr.io -u ${GHCR_USER} --password-stdin
                            docker push ${IMAGE_NAME}:${IMAGE_TAG}
                            docker push ${IMAGE_NAME}:${GIT_COMMIT_SHORT}
                            docker logout ghcr.io
                        '''
                    }
                }
            }
        }
        
        stage('Deploy to Dev') {
            when {
                branch 'develop'
            }
            steps {
                script {
                    echo "🚀 Deploying to DEV..."
                    sh '''
                        kubectl set image deployment/cats-dogs-api \
                            cats-dogs-api=${IMAGE_NAME}:${GIT_COMMIT_SHORT} \
                            --record \
                            -n dev || true
                        
                        kubectl rollout status deployment/cats-dogs-api -n dev --timeout=5m
                    '''
                }
            }
        }
        
        stage('Deploy to Staging') {
            when {
                branch 'staging'
            }
            input {
                message "Deploy to Staging?"
                ok "Deploy"
            }
            steps {
                script {
                    echo "🚀 Deploying to STAGING..."
                    sh '''
                        kubectl set image deployment/cats-dogs-api \
                            cats-dogs-api=${IMAGE_NAME}:${IMAGE_TAG} \
                            --record \
                            -n staging || true
                        
                        kubectl rollout status deployment/cats-dogs-api -n staging --timeout=5m
                    '''
                }
            }
        }
        
        stage('Deploy to Production') {
            when {
                branch 'main'
                expression {
                    return params.DEPLOY
                }
            }
            input {
                message "Deploy to PRODUCTION? ⚠️"
                ok "Deploy to Production"
            }
            steps {
                script {
                    echo "🚀 Deploying to PRODUCTION..."
                    sh '''
                        kubectl set image deployment/cats-dogs-api \
                            cats-dogs-api=${IMAGE_NAME}:${IMAGE_TAG} \
                            --record \
                            -n production || true
                        
                        kubectl rollout status deployment/cats-dogs-api -n production --timeout=5m
                    '''
                }
            }
        }
        
        stage('Smoke Tests') {
            when {
                expression {
                    return params.DEPLOY
                }
            }
            steps {
                script {
                    echo "✅ Running comprehensive smoke tests..."
                    sh '''
                        # Install smoke test dependencies
                        pip install requests
                        
                        # Get pod name and namespace based on deployment stage
                        NAMESPACE="production"
                        if [ "${GIT_BRANCH##*/}" == "staging" ]; then
                            NAMESPACE="staging"
                        elif [ "${GIT_BRANCH##*/}" == "develop" ]; then
                            NAMESPACE="dev"
                        fi
                        
                        echo "Testing in namespace: $NAMESPACE"
                        
                        # Port forward
                        kubectl port-forward -n $NAMESPACE svc/cats-dogs-api 8001:8000 > /dev/null 2>&1 &
                        PF_PID=$!
                        sleep 2
                        
                        # Run comprehensive smoke tests
                        python3 tests/smoke_test.py http://localhost:8001 \
                            --max-retries 30 \
                            --retry-delay 1 \
                            --test-image data/processed/train/cat/25.jpg
                        
                        TEST_RESULT=$?
                        
                        # Clean up port forwarding
                        kill $PF_PID 2>/dev/null || true
                        wait $PF_PID 2>/dev/null || true
                        
                        if [ $TEST_RESULT -ne 0 ]; then
                            echo "❌ Smoke tests failed with exit code: $TEST_RESULT"
                            exit $TEST_RESULT
                        fi
                        
                        echo "✅ All smoke tests passed!"
                    '''
                }
            }
        }
    }
    
    post {
        always {
            script {
                echo "📊 Cleaning up..."
                cleanWs()
            }
        }
        success {
            script {
                echo "✅ Pipeline succeeded!"
                // Send success notification
                emailext(
                    subject: "✅ Deployment Success: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                    body: '''
                        Build succeeded!
                        
                        Build Number: ${BUILD_NUMBER}
                        Build URL: ${BUILD_URL}
                        Image: ${IMAGE_NAME}:${IMAGE_TAG}
                    ''',
                    to: '${DEFAULT_RECIPIENTS}'
                )
            }
        }
        failure {
            script {
                echo "❌ Pipeline failed!"
                emailext(
                    subject: "❌ Deployment Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                    body: '''
                        Build failed!
                        
                        Build Number: ${BUILD_NUMBER}
                        Build URL: ${BUILD_URL}
                        Check logs for details.
                    ''',
                    to: '${DEFAULT_RECIPIENTS}'
                )
            }
        }
        unstable {
            script {
                echo "⚠️  Pipeline unstable (tests failed but build succeeded)"
            }
        }
    }
}
