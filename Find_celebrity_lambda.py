import json
import boto3
import logging
import io
import requests
#from botocore.vendored import requests
from PIL import Image, ImageDraw, ExifTags, ImageColor, ImageFont
#celebrity-names-for-selenium-bucket

def lambda_handler(event, context):
    id = ''
    if event :
        id =str(event["Records"][0]["s3"]["object"]["key"])
        splt = id.split(".")
        splt_id = splt[0]
    #id = 'id0000.jpg'
    #splt_id = 'id0000'
    s3_client = boto3.client('s3')
    #output bucket안에 잇는 모든 객체들 삭제
    delete_output_bucket(splt_id)
    #delete_sele_input_bucket(id) #트리거 다시 되게 하려고 지워주는 거임 ->이거 셀레니움 람다에서 지워줘야할거같은데 ;;
    
    names_string = ""
    unknown_points = []
    #pil라이브러리 및 celebrity api 실행
    input_bucket = 'input-for-user-upload-img-bucket'
    Key = id
    dict_Recognized, dict_Unrecognized, unknown_points = recognize_celebrities(Key,input_bucket,id,splt_id)
    names_string = crop_and_save_celebrity_face(dict_Recognized, Key, input_bucket,names_string,id,splt_id)
    crop_and_save_Unrecognized_face(dict_Unrecognized, Key, input_bucket,id)
    	
    print(unknown_points)
    	
    	
    #celebrity api에서 인식 실패한 unknown 버켓에 있는 이미지 detet 및 compare 실행
    unknown_bucket = 'unknown-cele-failed-img-bucket'
    objects = s3_client.list_objects(
        Bucket=unknown_bucket,
        Prefix = id,
        MaxKeys = 50,
    )
    #unknown 버킷에 이미지가 compare api 실행
    if(objects.get("Contents")):
    	#compare실패한 이미지에 넘버링해서 저장하기 위함
    	compare_failed_count = 1
    	i = 0
    	for content in objects['Contents']:
        	key = content['Key']
        	if key==id+'/':
        		continue
        	img = s3_client.get_object(Bucket=unknown_bucket,Key=key)
        	print('tttteeeeesssttt')
        	print(key)
        	gender = detect_face(unknown_bucket, key)
        	print(gender)
        
        	if gender == 'Male' :
        		success,names_string = compare_face('male-ref-image-for-compare-bucket','unknown-cele-failed-img-bucket',key,compare_failed_count,names_string,id,splt_id)
        	elif gender == 'Female' :
        		success,names_string = compare_face('female-ref-image-for-compare-bucket','unknown-cele-failed-img-bucket',key,compare_failed_count,names_string,id,splt_id)
        	else :
        		pass
        	
        	if success == 1:
        		draw_line_for_unknown(splt_id+'/'+"bounding_all_faces.jpg", "celebrity-result-img-bucket",unknown_points[i],id,splt_id)
        	#success가 0인경우 즉, compare에 실패한 경우 count
        	elif success == 0 :
        		compare_failed_count += compare_failed_count
        		
        		
        	i = i+1
    #크롤링을 위한 유명인 이름 String을 버켓에 저   	
    print(names_string)
    bucket = 'celebrity-names-for-selenium-bucket'
    s3 = boto3.client('s3')
    s3.put_object(
    	Body = names_string,
    	Bucket = bucket,
    	Key = splt_id + ".txt"  ## id 별로 sele input bucket에 txt파일 생성
    	)
    delete_input_bucket(id) # 트리거 다시 되게하려고 지워주는것. 사실 코드로 put object해도 트리거 되긴 하는듯.
    delete_unknown_bucket(id)
    
    return {
        'statusCode': 200,
        'body': 0
    }



def recognize_celebrities(photo, bucket,id,splt_id):

	client = boto3.client('rekognition')
	s3_client = boto3.client('s3')
	resource = boto3.resource('s3')

	dict_Recognized = {} # key : cele.api 결과로 나온 이름 / value : crop할 좌표 
	dict_Unrecognized = {} # key : unknown_i / value : crop할 좌표 

	# Load image from S3 bucket
	s3_connection = boto3.resource('s3')
	s3_object = s3_connection.Object(bucket,photo)
	s3_response = s3_object.get()

	stream = io.BytesIO(s3_response['Body'].read())
	image=Image.open(stream)

	#Call recognize_celebrities api  
	response = client.recognize_celebrities(
	Image = {'S3Object' : {'Bucket': bucket, 'Name': photo} })

	imgWidth, imgHeight = image.size  
	draw = ImageDraw.Draw(image)

	#만약에 cele 도 인식 못하고 , unrecog도 인식 못하면 for문 에러나지 않는지 테스트 ㄱㄱ
	for celebrityFaces in response['CelebrityFaces']:
		box = celebrityFaces['Face']['BoundingBox']
		left = imgWidth * box['Left']
		top = imgHeight * box['Top']
		width = imgWidth * box['Width']
		height = imgHeight * box['Height']

		tuple_bound = (round(left), round(top),
		round(width) + round(left), round(height) + round(top))
		name = celebrityFaces['Name']
		dict_Recognized[name] = tuple_bound

		points = (
			(left, top),
			(left + width, top),
			(left + width, top + height),
			(left , top + height),
			(left, top)

			)
		draw.line(points, fill = '#00d400', width = 2)
	i = 1
	points_tuple_list = []
	for celebrityFaces in response['UnrecognizedFaces']:
		
		box = celebrityFaces['BoundingBox']
		left = imgWidth * box['Left']
		top = imgHeight * box['Top']
		width = imgWidth * box['Width']
		height = imgHeight * box['Height']

		tuple_bound = (round(left), round(top),
		round(width) + round(left), round(height) + round(top))
		name = 'UnrecognizedFaces_' + str(i)
		i = i + 1
		dict_Unrecognized[name] = tuple_bound

		points = (
			(left, top),
			(left + width, top),
			(left + width, top + height),
			(left , top + height),
			(left, top)

			)
		draw.line(points, fill = '#d40000', width = 2)
		points_tuple_list.append(points)


	buffer = io.BytesIO()
	image.save(buffer , format = image.format)
	buffer.seek(0)
	s3_client.put_object(Bucket = 'celebrity-result-img-bucket', Key = splt_id+'/'+'bounding_all_faces.jpg', Body = buffer)
	#s3_client.put_object(Body = stream.getValue(), Bucket = 'finded-face-name', Key = 'bounding_all_fcaes.jpg')
	#image.show() #im.save같은걸로 저장할까 

	return dict_Recognized, dict_Unrecognized, points_tuple_list


# 
def crop_and_save_celebrity_face(dict_Recognized, photo, bucket, names_string,id,splt_id):
	client = boto3.client('rekognition')
	s3_client = boto3.client('s3')
	resource = boto3.resource('s3')

	# Load image from S3 bucket
	s3_connection = boto3.resource('s3')
	s3_object = s3_connection.Object(bucket,photo)
	s3_response = s3_object.get()

	stream = io.BytesIO(s3_response['Body'].read())
	image=Image.open(stream) # stream 이 jpg 이미지 라고 생각하자. 

	length_recognized = range(0,len(dict_Recognized))
	for i, key in zip(length_recognized, dict_Recognized.keys()):
		area = dict_Recognized[key]
		print(area)
		cropped_image = image.crop(area)
		
		buffer = io.BytesIO()
		cropped_image.save(buffer , format = image.format)
		buffer.seek(0)
		s3_client.put_object(Bucket = 'celebrity-result-img-bucket', Key = splt_id+"/"+get_translate(key) + '.jpg', Body = buffer)
		
		buffer = io.BytesIO()
		cropped_image.save(buffer , format = image.format)
		buffer.seek(0)
		s3_client.put_object(Bucket = 'img-for-database-bucket', Key = splt_id+"/"+get_translate(key) + '.jpg', Body = buffer)
		
		names_string = str(names_string)+"/"+str(get_translate(key))
	return names_string



def crop_and_save_Unrecognized_face(dict_Unrecognized, photo, bucket,id):
	client = boto3.client('rekognition')
	s3_client = boto3.client('s3')
	resource = boto3.resource('s3')

	# Load image from S3 bucket
	s3_connection = boto3.resource('s3')
	s3_object = s3_connection.Object(bucket,photo)
	s3_response = s3_object.get()

	stream = io.BytesIO(s3_response['Body'].read())
	image=Image.open(stream) # stream 이 jpg 이미지 라고 생각하자. 

	#print(len(dict_Unrecognized))
	length_unrecognized = range(1,len(dict_Unrecognized)+1)
	for i in length_unrecognized:
		area = dict_Unrecognized['UnrecognizedFaces_' + str(i)]
		print(area)
		cropped_image = image.crop(area)
		#resource.Bucket('unknown-face-img').upload_file(cropped_image, 'UnkonwnFaces_' + str(i) + '.jpg')

		buffer = io.BytesIO()
		cropped_image.save(buffer , format = image.format)
		buffer.seek(0)
		s3_client.put_object(Bucket = 'unknown-cele-failed-img-bucket', Key = id+'/'+'UnkonwnFaces_' + str(i) + '.jpg', Body = buffer)

		#cropped_image.show() #im.save같은걸로 저장할까

def delete_output_bucket(splt_id):
	s3_client = boto3.client('s3')
	output_bucket = 'celebrity-result-img-bucket'
	response = s3_client.list_objects(
        Bucket=output_bucket,
        Prefix = splt_id,
        MaxKeys = 50,
    )

	if(response.get("Contents")):
		for content in response['Contents']:
			Key=content['Key']
			delete = s3_client.delete_objects(
				Bucket = output_bucket,
				Delete={
					'Objects' : [
						{
							'Key' : Key,
						},
					],
					'Quiet' : False,
				},
			)
	s3_client.put_object(
		Bucket = output_bucket,
		Key = splt_id+'/'
		)
        
def delete_input_bucket(id):
	s3_client = boto3.client('s3')
	input_bucket = 'input-for-user-upload-img-bucket'

	Key=id
	delete = s3_client.delete_objects(
		Bucket = input_bucket,
		Delete={
			'Objects' : [
				{
					'Key' : Key,
				},
			],
			'Quiet' : False,
		},
	)

def delete_unknown_bucket(id):
	s3_client = boto3.client('s3')
	unknown_bucket = 'unknown-cele-failed-img-bucket'
	response = s3_client.list_objects(
        Bucket=unknown_bucket,
        Prefix = id,
        MaxKeys = 50,
    )

	if(response.get("Contents")):
		for content in response['Contents']:
			Key=content['Key']
			delete = s3_client.delete_objects(
				Bucket = unknown_bucket,
				Delete={
					'Objects' : [
						{
							'Key' : Key,
						},
					],
					'Quiet' : False,
				},
			)
	s3_client.put_object(
		Bucket = unknown_bucket,
		Key = id+'/'
		)

def delete_sele_input_bucket():
	s3_client = boto3.client('s3')
	input_bucket = 'celebrity-names-for-selenium-bucket'
	response = s3_client.list_objects(
        Bucket=input_bucket,
        MaxKeys = 50,
    )

	if(response.get("Contents")):
		for content in response['Contents']:
			Key=content['Key']
			delete = s3_client.delete_objects(
				Bucket = input_bucket,
				Delete={
					'Objects' : [
						{
							'Key' : Key,
						},
					],
					'Quiet' : False,
				},
			)	
			
			
def detect_face(bucket, key) :
    rek_client = boto3.client('rekognition')
    s3_client = boto3.client('s3')
    s3_resource = boto3.resource('s3')
    print('제발 ')
    print(key)
    img = s3_client.get_object(Bucket=bucket,Key=key)
    response = rek_client.detect_faces(
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': key,
            },
        },
        Attributes=[
            'ALL',
        ]
    )
    #얼굴/미얼굴 필터링 : try -> 얼굴임, except -> 얼굴아님
    try :
        return response['FaceDetails'][0]['Gender']['Value']
    except :
        return 'No_Face'
        
        
def compare_face(SRC_Bucket, TARGET_Bucket, TARGET_key,compare_failed_count,names_string,id,splt_id) :
    rek_client = boto3.client('rekognition')
    s3_client = boto3.client('s3')
    s3_resource = boto3.resource('s3')
    
    src_bucket = SRC_Bucket
    target_bucket = TARGET_Bucket
    target_key = TARGET_key
    img = s3_client.get_object(Bucket=target_bucket,Key=target_key)
    
    success = 0
            
    src_objects = s3_client.list_objects(
        Bucket=src_bucket,
        MaxKeys = 50,
    )
    for src_content in src_objects['Contents']:
        src_key = src_content['Key']
        response=rek_client.compare_faces(SimilarityThreshold=80,
							            SourceImage={'S3Object': {'Bucket': src_bucket,'Name': src_key} },
									    TargetImage={'S3Object': {'Bucket': target_bucket,'Name': target_key} })
				
        if response['FaceMatches']:
            #print(response['FaceMatches'])
            similarity = response['FaceMatches'][0]['Similarity']
            print(similarity)
                    
            if similarity >= 70 :
            	success = 1
            	s3_client.put_object(
            		Body = img['Body'].read(),
            		Bucket = 'celebrity-result-img-bucket',
            		Key = splt_id+'/'+src_key
            	)
            	s3_client.put_object(
            		Body = img['Body'].read(),
            		Bucket = 'img-for-database-bucket',
            		Key = splt_id+'/'+src_key
            	)
            	names_string = names_string+"/"+str(src_key).split('.')[0]
    if success == 0:
    	s3_client.put_object(
    		Body = img['Body'].read(),
    		Bucket = 'celebrity-result-img-bucket',
    		Key = splt_id+'/'+'compare에서도 실패'+str(compare_failed_count)+'.jpg'
    	)
    	
    return success,names_string
    
#언노운을 위한 ㅎ,,,
def draw_line_for_unknown(photo, bucket, points_tuple,id,splt_id):
   client = boto3.client('rekognition')
   s3_client = boto3.client('s3')
   resource = boto3.resource('s3')

   s3_connection = boto3.resource('s3')
   s3_object = s3_connection.Object(bucket,photo)
   s3_response = s3_object.get()

   stream = io.BytesIO(s3_response['Body'].read())
   image=Image.open(stream)

   imgWidth, imgHeight = image.size  
   draw = ImageDraw.Draw(image)

   draw.line(points_tuple, fill = '#00d400', width = 2)


   buffer = io.BytesIO()
   image.save(buffer , format = image.format)
   buffer.seek(0)
   s3_client.put_object(Bucket = 'celebrity-result-img-bucket', Key = splt_id+'/'+'bounding_all_faces.jpg', Body = buffer)
   
#파파고 api에연   
def get_translate(text):
    client_id = "" # <-- client_id 기입
    client_secret = "" # <-- client_secret 기입

    data = {'text' : text,
            'source' : 'en',
            'target': 'ko'}

    url = "https://openapi.naver.com/v1/papago/n2mt"

    header = {"X-Naver-Client-Id":"비밀",
              "X-Naver-Client-Secret":"비밀"}

    response = requests.post(url, headers=header, data=data)
    rescode = response.status_code

    if(rescode==200):
        send_data = response.json()
        trans_data = (send_data['message']['result']['translatedText'])
        return trans_data
    else:
        print("Error Code:" , rescode)