import json
import boto3

def lambda_handler(event, context):
    resource = boto3.resource('s3')
    client = boto3.client('s3')
    rekog = boto3.client('rekognition')
    bucket = 'all-ref-image-for-compare-bucket'
    
    objects = client.list_objects(
        Bucket=bucket,
        MaxKeys = 50,
    )
    #cele 돌리기
    for content in objects['Contents']:
        cele_success = 0
        img = client.get_object(Bucket=bucket,Key=content['Key'])
        response = rekog.recognize_celebrities(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': content['Key']
                }
            }
        )
        if(not response['CelebrityFaces']):
            pass
        else:
            confidence = response['CelebrityFaces'][0]['Face']['Confidence']
            if(confidence > 80):
                cele_success = 1
            else:
                pass
                
        #cele 실패 -> 남/여ref 이미지 버킷에 저장
        if cele_success == 0:
            response_for_detect = rekog.detect_faces(
                Image={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': content['Key'],
                    },
                },
                Attributes=[
                    'ALL',
                ]
            )
            Gender = response_for_detect['FaceDetails'][0]['Gender']['Value']

            #분류에 따라 새로운 버킷에 이미지 저장
            if(Gender == 'Male'):
                client.put_object(
    	            Body = img['Body'].read(),
    	            Bucket = 'male-ref-image-for-compare-bucket',
    	            Key = content['Key'].split()[1]+'.jpg'
    	        )
            else:
                client.put_object(
    	            Body = img['Body'].read(),
    	            Bucket = 'female-ref-image-for-compare-bucket',
    	            Key = content['Key'].split()[1]+'.jpg'
    	        )
            print(content['Key'].split()[1]+'.jpg')
            
        #cele 성공 -> ref 이미지 저장X
        else:
            name = response['CelebrityFaces'][0]['Name']
            confidence = response['CelebrityFaces'][0]['Face']['Confidence']
            print(name, " ", confidence)
        
        

    return {
        'statusCode': 200,
        'body': 0
    }
