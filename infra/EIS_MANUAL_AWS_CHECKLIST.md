# EIS Manual AWS Checklist

Use this when deploying from the AWS Console.

## Files You Need

- Lambda source code to copy-paste: `backend/explanation_lambda.py`
- DynamoDB CloudFormation template: `infra/eis-dynamodb.yaml`
- IAM policy: `infra/eis-lambda-policy.json`
- Lambda test event: `backend/explanation-test-event.json`

## Manual Steps

1. Create DynamoDB table using `infra/eis-dynamodb.yaml`.
   - Stack name: `rrb-eis-cache`
   - Table name: `rrb_explanations`

2. Create Lambda.
   - Function name: `rrb-explanation-service`
   - Runtime: Python 3.12
   - Handler: `explanation_lambda.lambda_handler`
   - Timeout: 60 seconds
   - Memory: 512 MB

3. Add Lambda source code.
   - In AWS Lambda Code tab, create/open file exactly named `explanation_lambda.py`
   - Copy all code from local file `backend/explanation_lambda.py`
   - Paste into AWS Lambda editor
   - Click `Deploy`

4. Add environment variables.
   - `EXPLANATIONS_TABLE=rrb_explanations`
   - `BEDROCK_MODEL_ID=apac.amazon.nova-pro-v1:0`
   - `EXPLANATION_GENERATION_VERSION=eis-v1`
   - `ALLOWED_ORIGIN=*`

Important:
- Do not add `AWS_REGION` manually in Lambda environment variables.
- AWS reserves `AWS_REGION`; Lambda provides it automatically.

5. Attach IAM policy.
   - Use `infra/eis-lambda-policy.json`
   - Replace `YOUR_ACCOUNT_ID` with your AWS account ID first.

6. Add API Gateway route.
   - Route: `POST /explanation`
   - Integration: `rrb-explanation-service`
   - Deploy stage: `prod`

7. Test Lambda with:
   - `backend/explanation-test-event.json`

8. Test app.
   - Submit a quiz.
   - Click `Show Solution`.
   - First request should generate.
   - Second request should return cached.
