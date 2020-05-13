#!/usr/bin/env python3

from aws_cdk import core

from vaquita.vaquita_stack import VaquitaStack

app = core.App()
VaquitaStack(app, "vaquita", env={'region': 'eu-central-1'})

app.synth()
