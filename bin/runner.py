# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import boto3
import uuid


# List of regions where we have deployed the CloudFormation stack
regions = [
    {
      'name': 'us-east-1',
      'stackName': 'dlt-fargate',
      'taskCount': 3
    },
    {
      'name': 'us-east-2',
      'stackName': 'dlt-fargate',
      'taskCount': 3
    },
    {
      'name': 'us-west-2',
      'stackName': 'dlt-fargate',
      'taskCount': 3
    }
]


def start_distributed_load_test():
    run_id = str(uuid.uuid4())
    print('Started new load test with runId = {}'.format(run_id))

    for region in regions:

        cloud_formation = boto3.client('cloudformation', region_name=region['name'])
        ecs = boto3.client('ecs', region_name=region['name'])

        print('Describing CloudFormation stack {} in region {}'.format(region['stackName'], region['name']))
        stacks = cloud_formation.describe_stacks(
            StackName=region['stackName']
        )

        if not stacks['Stacks']:
            print("CloudFormation stack {} not found in region {}".format(region['stackName'], region['name']))
            exit(0)

        stack = stacks['Stacks'][0]
        outputs = stack['Outputs']
        stack_outputs = {}

        print('Extracting cluster values from CloudFormation stack')
        for output in outputs:
            stack_outputs[output['OutputKey']] = output['OutputValue']

        print('Scheduling tasks in region {}'.format(region['name']))
        response = ecs.run_task(
            cluster=stack_outputs['FargateClusterName'],
            taskDefinition=stack_outputs['TaskDefinitionArn'],
            count=region['taskCount'],
            startedBy=run_id,
            group=run_id,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'assignPublicIp': 'ENABLED',
                    'securityGroups': [stack_outputs['TaskSecurityGroup']],
                    'subnets': [
                        stack_outputs['SubnetA'],
                        stack_outputs['SubnetB'],
                        stack_outputs['SubnetC']
                    ]
                }
            }
        )

        if not response or response['failures']:
            print('Failed to schedule tasks')
            exit(0)

        for task in response['tasks']:
            print('Task scheduled {}', task['taskArn'])


if __name__ == '__main__':
    start_distributed_load_test()