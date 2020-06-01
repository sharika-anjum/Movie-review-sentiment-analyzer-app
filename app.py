from flask import Flask, request,render_template,redirect, url_for
import requests,re
from bs4 import BeautifulSoup as bs
import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import re # for regex

# pkl
import pickle

# headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'}

word_list = pickle.load(open('bow1.pkl','rb')) #gets the downloaded file
clf = pickle.load(open('model1.pkl','rb')) #gets the downloaded file

def scraped(url):
    req = requests.get(url).text #stores the entire html code on the webpage opened on that link
    idx,title,year = [],[],[] #3 lists created
    pattern = r'[0-9]{4}' #stores 4 digits
    soup = bs(req,'html.parser') #makes the html code in proper format
    try:
        table = soup.find('table').find_all('tr') #from the tables it fetches all the tr tag information
        if len(table) < 15: #finds out how many tr elements it got
            for i in range(len(table)):
                idx.append(str(table[i].find_all('a')[1]['href']).split('/')[-2]) #from each <a href> tag it removes / and stores only the movie Id and stores it in idx
                title.append(table[i].find_all('a')[1].text.strip()) #it just gets the <a> tag word and stores it
                try:
                    year.append(re.findall(pattern, table[i].find_all('td')[1].text)[0])#years are always a 4 digit word. so it gets all the 4 digits that is under <td> tag
                except:
                    year.append('-')
        else:
            for i in range(len(table[:16])): #if there are more than 10 results. it will still take the first 10 results
                idx.append(str(table[i].find_all('a')[1]['href']).split('/')[-2])
                title.append(table[i].find_all('a')[1].text.strip())
                try:
                    year.append(re.findall(pattern,table[i].find_all('td')[1].text)[0])
                except:
                    year.append('-')
    except:
        abc = "No tables"
    return idx,title,year

def scraped_revs(url1,url2):
    req = requests.get(url1).text #stores the entire html code of the page
    req2 = requests.get(url2).text #stores the entire html code of the page

    genres,revs = [],[]
    soup = bs(req,'html.parser') #formats the code
    soup2 = bs(req2,'html.parser')   #formats the code     # For reviews
    title = soup.find('div', {"class":"title_wrapper"}).find_all('h1')[0].text #stores the thing stored in div tag with class title_wrapper with h1 tag
    try:
        ratings = soup.find('div', {"class":"ratingValue"}).find_all('span')[0].text #stores the thing stored in div tag with class ratingValue with span attribute
    except:
        ratings = "Not Rated"
    try:
        duration = soup.find('div', {"class":"subtext"}).find_all('time')[0].text.strip() #similarly stores the duration of the movie
    except:
        duration = "No Information Available"
    try:
        lst = soup.find('div', {"class":"subtext"}).find_all('a')
        for i in range(len(lst)-1):
            genres.append(lst[i].text)    #sameway stores the genres
        gen = ",".join(genres)
    except:
        gen = "No Information Available"
    try:
        date = lst[-1].text.strip()  #release date
    except:
        date = "No Information Available"
    try:
        image = soup.find('div', {"class":"poster"}).find_all('img')[0]['src']  #movie banner
    except:
        image = "No Image Available"
    try:
        rev_div = soup2.find('div',{"class":"lister-list"}).find_all('div',{"class":"lister-item-content"})
        for i in range(len(rev_div)):
            rev_rate = rev_div[i].find_all('span')[1].text
            if len(rev_rate.split(" ")) == 1:
                rev_ratings = rev_rate  #review ratings
            else:
                rev_ratings = "Not rated"
            rev_title = rev_div[i].find_all('a',{"class":"title"})[0].text.strip()   #review title of each person
            user = rev_div[i].find_all('a')[1].text.strip()  #reviewer name
            rev_rev = rev_div[i].find('div',{"class":"text show-more__control"}).text.strip() #review

            rev_d = {'ratings':rev_ratings,'title':rev_title,'user':user,'review':rev_rev}  #storing everything in one dataframe
            revs.append(rev_d)
    except:
        revs.append("No Reviewers yet")
    return title,ratings,duration,gen,date,image,revs

# TEXT PREPROCESSING FUNCTIONS
def clean(text):  #removing html tags
    cleaned = re.compile(r'<.*?>')
    return re.sub(cleaned,'',text)

def is_special(text): #removing special characters
    rem = ''
    for i in text:
        if i.isalnum():
            rem = rem + i
        else:
            rem = rem + ' '
    return rem

def to_lower(text): #making the tests to lower case
    return text.lower()

def rem_stopwords(text): #removing the stop words using nlp
    stop_words = set(stopwords.words('english'))
    words = word_tokenize(text)
    return [w for w in words if w not in stop_words]

def stem_txt(text): #doing stemming using nlp
    ss = SnowballStemmer('english')
    return " ".join([ss.stem(w) for w in text])

app = Flask(__name__)

@app.route('/')
def home(): #function for the home page
    return render_template("index.html")

@app.route('/choices', methods=['POST'])
def choices():
    title = request.form.get('movie') #gets the movie name
    if len(title.split()) == 1: #gets the no. of words and checks it
        url = 'https://www.imdb.com/find?s=tt&q={}&ref_=nv_sr_sm'.format(title) #goes to the url
    else:
        title_str = "+".join(title.split()) #if the no. of words is more than 1 then it adds to the url by putting a + in between the words in the url
        url = 'https://www.imdb.com/find?s=tt&q={}&ref_=nv_sr_sm'.format(title_str)

    idx,movie,yor = scraped(url)
    return render_template('choices.html',idx=idx,movie=movie,yor=yor)

@app.route('/review/<string:type>')
def review(type): #type variable is nothing but the movie id
    url1 = "https://www.imdb.com/title/{}/?ref_=fn_tt_tt_1".format(type) #stores the movie page with its info
    url2 = "https://www.imdb.com/title/{}/reviews?ref_=tt_urv".format(type) #stores the movie review page
    title,ratings,duration,genres,date,image,revs = scraped_revs(url1=url1,url2=url2)
    labels = []

    for r in revs:
        f5 = r['review']
        inp = []
        for i in word_list:
            inp.append(f5.count(i[0]))  #predicting sentiment
        label = clf.predict(np.array(inp).reshape(1,1000))[0]

        rate = r['ratings']
        if rate in ['8','9','10']:
            labels.append(1)  #finding poor rating or good rating by viewers
        elif rate in ['1','2','3']:
            labels.append(0)
        else:
            if label == 1:
                labels.append(label)
            else:
                labels.append(-1)
    if len(labels):
        sent_score = (len([i for i, x in enumerate(labels) if x == 1])/len(labels))*10  #finding sentiment score
    else:
        sent_score = 0
    return render_template('review.html',title=title,ratings=ratings,duration=duration,genres=genres,date=date,image=image,revs=revs,labels=labels,sent_score=sent_score)

if __name__=="__main__":
    app.run(debug=True)