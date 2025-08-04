import aws_cdk as core
import aws_cdk.assertions as assertions

from mp4_small_analyser_cdk.mp4_small_analyser_cdk_stack import Mp4SmallAnalyserCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in mp4_small_analyser_cdk/mp4_small_analyser_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Mp4SmallAnalyserCdkStack(app, "mp4-small-analyser-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
