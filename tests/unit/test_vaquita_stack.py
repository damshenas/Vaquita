import json
import pytest

from aws_cdk import core
from vaquita.vaquita_stack import VaquitaStack


def get_template():
    app = core.App()
    VaquitaStack(app, "vaquita")
    return json.dumps(app.synth().get_stack("vaquita").template)


def test_sqs_queue_created():
    assert("AWS::SQS::Queue" in get_template())


def test_sns_topic_created():
    assert("AWS::SNS::Topic" in get_template())
