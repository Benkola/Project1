provider "aws" {
  region = var.region
}

locals {
  project = "ttsr"
  stage   = "dev"
  name    = "${local.project}-${local.stage}"
}

# KMS key (placeholder for secrets)
resource "aws_kms_key" "app" {
  description             = "${local.name} secrets"
  deletion_window_in_days = 7
}

# DynamoDB (events)
resource "aws_dynamodb_table" "events" {
  name         = "${local.name}-events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  tags = { Project = local.project, Stage = local.stage }
}

# IAM role for Lambdas
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

# Minimal policy: CloudWatch logs + DynamoDB access
data "aws_iam_policy_document" "lambda_policy" {
  statement {
    actions   = ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"]
    resources = ["*"]
  }

  statement {
    actions   = ["dynamodb:GetItem","dynamodb:PutItem"]
    resources = [aws_dynamodb_table.events.arn]
  }
}

resource "aws_iam_role_policy" "lambda_inline" {
  name   = "${local.name}-lambda-inline"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_policy.json
}

# Package Lambdas from api/handlers
data "archive_file" "score_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../api/handlers"
  output_path = "${path.module}/build/score.zip"
}

data "archive_file" "get_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../api/handlers"
  output_path = "${path.module}/build/get_event.zip"
}

data "archive_file" "health_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../api/handlers"
  output_path = "${path.module}/build/health.zip"
}

# Lambda functions
resource "aws_lambda_function" "score" {
  function_name    = "${local.name}-score"
  role             = aws_iam_role.lambda.arn
  handler          = "score_handler.handler"
  runtime          = "python3.11"
  filename         = data.archive_file.score_zip.output_path
  source_code_hash = data.archive_file.score_zip.output_base64sha256
  timeout          = 10

  environment {
    variables = {
      TABLE  = aws_dynamodb_table.events.name
      TENANT = "demo"
    }
  }
}

resource "aws_lambda_function" "get_event" {
  function_name    = "${local.name}-get-event"
  role             = aws_iam_role.lambda.arn
  handler          = "get_event.handler"
  runtime          = "python3.11"
  filename         = data.archive_file.get_zip.output_path
  source_code_hash = data.archive_file.get_zip.output_base64sha256
  timeout          = 10

  environment {
    variables = {
      TABLE  = aws_dynamodb_table.events.name
      TENANT = "demo"
    }
  }
}

resource "aws_lambda_function" "health" {
  function_name    = "${local.name}-health"
  role             = aws_iam_role.lambda.arn
  handler          = "health_handler.handler"
  runtime          = "python3.11"
  filename         = data.archive_file.health_zip.output_path
  source_code_hash = data.archive_file.health_zip.output_base64sha256
  timeout          = 5
}

# API Gateway REST
resource "aws_api_gateway_rest_api" "api" {
  name        = "${local.name}-api"
  description = "TTSR REST API"
}

# /v1
resource "aws_api_gateway_resource" "v1" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "v1"
}

# /v1/health GET
resource "aws_api_gateway_resource" "health" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "health"
}

resource "aws_api_gateway_method" "health_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "health_get" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.health.id
  http_method             = aws_api_gateway_method.health_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.health.invoke_arn
}

# /v1/score POST
resource "aws_api_gateway_resource" "score" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "score"
}

resource "aws_api_gateway_method" "score_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.score.id
  http_method   = "POST"
  authorization = "NONE" # Day 4: change to CUSTOM or COGNITO
}

resource "aws_api_gateway_integration" "score_post" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.score.id
  http_method             = aws_api_gateway_method.score_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.score.invoke_arn
}

# /v1/events/{id} GET
resource "aws_api_gateway_resource" "events" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "events"
}

resource "aws_api_gateway_resource" "event_id" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.events.id
  path_part   = "{id}"
}

resource "aws_api_gateway_method" "event_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.event_id.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.path.id" = true
  }
}

resource "aws_api_gateway_integration" "event_get" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.event_id.id
  http_method             = aws_api_gateway_method.event_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.get_event.invoke_arn

  request_parameters = {
    "integration.request.path.id" = "method.request.path.id"
  }
}

# Lambda permissions so API Gateway can invoke them
resource "aws_lambda_permission" "allow_apigw_health" {
  statement_id  = "AllowAPIGatewayInvokeHealth"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.health.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/GET/v1/health"
}

resource "aws_lambda_permission" "allow_apigw_score" {
  statement_id  = "AllowAPIGatewayInvokeScore"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.score.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/POST/v1/score"
}

resource "aws_lambda_permission" "allow_apigw_event" {
  statement_id  = "AllowAPIGatewayInvokeEvent"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_event.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/GET/v1/events/*"
}

# Deploy stage
resource "aws_api_gateway_deployment" "deploy" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  triggers = {
    redeploy = timestamp()
  }

  depends_on = [
    aws_api_gateway_integration.health_get,
    aws_api_gateway_integration.score_post,
    aws_api_gateway_integration.event_get
  ]
}

resource "aws_api_gateway_stage" "stage" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  deployment_id = aws_api_gateway_deployment.deploy.id
  stage_name    = local.stage
  variables     = { project = local.project }
}
