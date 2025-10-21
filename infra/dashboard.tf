resource "aws_cloudwatch_dashboard" "ttsr" {
  dashboard_name = "${local.name}-dash"

  # Proper metric widgets: must include "region" and "metrics"
  dashboard_body = jsonencode({
    widgets = [
      {
        "type" : "metric",
        "x" : 0, "y" : 0, "width" : 12, "height" : 6,
        "properties" : {
          "region" : var.region,
          "view" : "timeSeries",
          "title" : "API 5xx & Latency",
          "stat" : "Sum",
          "period" : 300,
          "metrics" : [
            ["AWS/ApiGateway", "5XXError", "ApiName", aws_api_gateway_rest_api.api.name],
            ["AWS/ApiGateway", "Latency", "ApiName", aws_api_gateway_rest_api.api.name]
          ]
        }
      },
      {
        "type" : "metric",
        "x" : 12, "y" : 0, "width" : 12, "height" : 6,
        "properties" : {
          "region" : var.region,
          "view" : "timeSeries",
          "title" : "Lambda score() Errors & Duration",
          "stat" : "Average",
          "period" : 300,
          "metrics" : [
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.score.function_name],
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.score.function_name]
          ]
        }
      }
    ]
  })
}
