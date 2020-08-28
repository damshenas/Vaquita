#!/usr/bin/env python3

from aws_cdk import core

from stack.cdk import VaquitaStack

app = core.App()
VaquitaStack(app, "vaquita", env={'region': 'eu-central-1'})

app.synth()
