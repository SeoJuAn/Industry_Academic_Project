from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import json
#import multiprocessing
from multiprocessing import Process, Lock, Manager
import multiprocessing as mp
import urllib.parse
import urllib.request
import boto3

from itertools import combinations


def get_driver():
	chrome_options = Options()
	chrome_options.add_argument('--headless')
	chrome_options.add_argument('--no-sandbox')
	chrome_options.add_argument('--disable-gpu')
	chrome_options.add_argument('--window-size=1280x1696')
	chrome_options.add_argument('--user-data-dir=/tmp/user-data')
	chrome_options.add_argument('--hide-scrollbars')
	chrome_options.add_argument('--enable-logging')
	chrome_options.add_argument('--log-level=0')
	chrome_options.add_argument('--v=99')
	chrome_options.add_argument('--single-process')
	chrome_options.add_argument('--data-path=/tmp/data-path')
	chrome_options.add_argument('--ignore-certificate-errors')
	chrome_options.add_argument('--homedir=/tmp')
	chrome_options.add_argument('--disk-cache-dir=/tmp/cache-dir')
	chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')
	chrome_options.binary_location = "/opt/python/bin/headless-chromium"

	driver = webdriver.Chrome('/opt/python/bin/chromedriver', chrome_options=chrome_options)
	return driver




def get_person_info_url(cele_name):
	base_url = "비밀"
	plus_url = urllib.parse.quote_plus(cele_name)
	url = base_url + plus_url

	search_html = urllib.request.urlopen(url).read()
	search_soup = BeautifulSoup(search_html, 'html.parser')
	search_sp = search_soup.find_all("a", class_ = "btn_txt_more")

	person_info_url = ""
	for i in search_sp:
		person_info_url = i.get("href")
	
	try:
		split_list = person_info_url.split('=')
		naver_id = int(split_list[len(split_list)-1])

	except:
		naver_id = 404


	return person_info_url, naver_id


def selenium_run(return_list, person_info_url, cele_name, naver_id):
	
	if(naver_id == 404):
		dict_person_work = {}
	
		dict_person_work["cele_name"] = cele_name
		dict_person_work["cele_id"] = naver_id
		dict_person_work["cele_item"] = []
		return_list.append(dict_person_work)
		return 0
	
	
	driver = get_driver()
	driver.get(person_info_url)


	list_person_work = []
	

	broad_names = driver.find_element_by_css_selector("#listUI_76").find_elements_by_tag_name("li")
	broad_img_urls = driver.find_element_by_css_selector("#listUI_76").find_elements_by_xpath("li/div/a/img")
	for name, url in zip(broad_names, broad_img_urls):
		temp_dict = {}

		Name = name.text.split("\n")[0]
		Url = url.get_attribute("src")

		temp_dict["title"] = Name
		temp_dict["img_url"] = Url
		temp_dict["category"] = "Broad&Drama" 
		list_person_work.append(temp_dict)
		
	while(True):
		try:
			nextBtn = driver.find_element_by_css_selector(
				"#pagination_76>span.bt_next>a")
			nextBtn.click()
			time.sleep(0.1)
			broad_names = driver.find_element_by_css_selector("#listUI_76").find_elements_by_tag_name("li")
			broad_img_urls = driver.find_element_by_css_selector("#listUI_76").find_elements_by_xpath("li/div/a/img")
			for name, url in zip(broad_names, broad_img_urls):
				temp_dict = {}

				Name = name.text.split("\n")[0]
				Url = url.get_attribute("src")

				temp_dict["title"] = Name
				temp_dict["img_url"] = Url
				temp_dict["category"] = "Broad&Drama" 
				list_person_work.append(temp_dict)
		except:
			break

#*****************************************

	movie_names = driver.find_element_by_css_selector("#listUI_78").find_elements_by_tag_name("li")
	movie_img_urls = driver.find_element_by_css_selector("#listUI_78").find_elements_by_xpath("li/div/a/img")

	for name, url in zip(movie_names, movie_img_urls):
		temp_dict = {}

		Name = name.text.split("\n")[0]
		Url = url.get_attribute("src")

		temp_dict["title"] = Name
		temp_dict["img_url"] = Url
		temp_dict["category"] = "Movie" 
		list_person_work.append(temp_dict)

	
	while(True):
		try:
			nextBtn = driver.find_element_by_css_selector(
				"#pagination_78>span.bt_next>a")
			nextBtn.click()
			time.sleep(0.1)
			movie_names = driver.find_element_by_css_selector("#listUI_78").find_elements_by_tag_name("li")
			movie_img_urls = driver.find_element_by_css_selector("#listUI_78").find_elements_by_xpath("li/div/a/img")
			for name, url in zip(movie_names, movie_img_urls):
				temp_dict = {}
	
				Name = name.text.split("\n")[0]
				Url = url.get_attribute("src")

				temp_dict["title"] = Name
				temp_dict["img_url"] = Url
				temp_dict["category"] = "Movie" 
				list_person_work.append(temp_dict)

		except:
			break

	dict_person_work = {}
	
	dict_person_work["cele_name"] = cele_name
	dict_person_work["cele_id"] = naver_id
	dict_person_work["cele_item"] = list_person_work


	
	
	driver.close()
	
	return_list.append(dict_person_work)
	
	
	#print(dump_string)
	
	#gv_str = gv_str + str(dict_person_work)
	#gv_list.append(dict_person_work)
	#print(gv_list)
	#return dump_string
	#s3 = boto3.client('s3')
	#s3.put_object(Bucket = 'selenium-result-bucket', Key = 'id값.json', Body = dump_string)


def append_nest_dict (gv_list):
	### 중첩 찾는 함수###
	print(len(gv_list))

	if(len(gv_list) == 0 or len(gv_list) == 1):
	    return gv_list
	else:
	    
	# 인물이 한개만 있으면 실행 ㄴㄴ . 인물이 아예 없어도 실행 ㄴㄴ
	# 인물이 두개 이상 있을 때만  !!!! 실행 되도록 

	    list_all_cele_work = []
	    list_key = []
	    for i in range(0, len(gv_list)):
	        #items = gv_list[i]["title"]
	        items = gv_list[i]["cele_item"]
	        dicts = {gv_list[i]["cele_name"] : []}
	        list_key.append(gv_list[i]["cele_name"])
	        for j in items :
	            dicts[gv_list[i]["cele_name"]].append(j["title"])
	        list_all_cele_work.append(dicts)

	    #print(list_all_cele_work)
	    dump_string = json.dumps(list_all_cele_work, indent = 4, ensure_ascii = False)
	    #print(dump_string)



	    for i in range(1, len(gv_list)):

	        for j in combinations(list_all_cele_work, i+1): #10번돌고 

	            list_nested = list(j)
	            result_list = []
	            key_list = [] # 
	            #key_stirng = ''

	            for k in list_nested: #2번돌고 
	                work_list = list(k.values())
	                key = list(k.keys())
	                key_list.append(key[0]) # 
	                #key_string = key_string + ' ' + key[0]
	                result_list = work_list[0]

	            for x in list_nested:
	                work_list = list(x.values())
	                result_list = set(result_list) & set(work_list[0])
	            
	            
	            if not(result_list):
	                pass
	            else:
	                dict_person_work = {}
	                dict_person_work["cele_name"] = ' '.join(key_list) #key_list 
	                list_person_work = []
	                for i in gv_list:
	                    
	                    if(i["cele_name"] == key_list[0]):  
	                        for j in i["cele_item"]:
	                            temp_dict = {}
	                            for k in result_list:
	                                if(j["title"] == k):
	                                    temp_dict["title"] = k
	                                    temp_dict["img_url"] = j["img_url"]
	                                    temp_dict["category"] = j["category"]
	                                    list_person_work.append(temp_dict)
	         

	                dict_person_work["cele_item"] = list_person_work
	                gv_list.append(dict_person_work)
	            

	    return gv_list


def lambda_handler(event, context):
	namestring = event['key']
	cele_name = namestring.split(' ')
	
	
	
	#del cele_name[0]
	print(cele_name)
	"""
	#배우 이름 담을 리스트
	names = []
	print(len(event))
	for i in range(len(event)) :
		print(event['key'+str(i+1)])
		names.append(event['key'+str(i+1)])
	    
	cele_name = names
	del cele_name[0]
    """
    
    
	#names에 담긴 이름들로 상현이의 기가맥힌 seleniuam 알고리즘 돌려서 결과값을 json 형태로 받아냄

	#cele_name = ["박보영", "김영광", "송중기"] #multiple cele name list   꺼꾸로 출력되네
	url_list = [] #bs4 로 찾아준 개인별 url 리스트 
	id_list = [] #bs4 로 찾아준 개인별 고유 naver id 리스트 
	
	#bs4
	for name in cele_name:
		person_info_url, naver_id = get_person_info_url(name)
		url_list.append(person_info_url)
		id_list.append(naver_id)

	manager = Manager()
	return_list = manager.list()
	
	#selenium
	procs = []
	for url, name, nv_id in zip(url_list, cele_name, id_list):
		proc = Process(target=selenium_run, args=(return_list, url, name, nv_id))
		procs.append(proc)
		proc.start()

	
	for proc in procs:
		proc.join()
	

	return_list = append_nest_dict(return_list)


	
	#print (len(return_list))
	
	#return_dict = return_list[0]
	#print(return_list)
	#for i in range(1, len(return_list)):
	#	return_dict.update(return_list[i])
	
	dump_string = json.dumps(list(return_list), indent = 4, ensure_ascii = False)
	
	return {
		'statusCode': 200,
		'body': json.loads(dump_string),
		"headers": {
			"Content-Type": "application/json"
		},
		"isBase64Encoded" : False
		
	}
