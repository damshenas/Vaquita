#!/usr/bin/env python3

from aws_cdk import core

from vaquita.vaquita_stack import VaquitaStack


app = core.App()
VaquitaStack(app, "vaquita", env={'region': 'us-west-2'})

app.synth()
