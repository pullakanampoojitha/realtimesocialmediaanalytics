from flask import Flask,render_template,request,session,redirect,jsonify
from pymongo import MongoClient
import boto3
from flask_cors import CORS

 
s3 = boto3.client('s3')
comprehend = boto3.client('comprehend')

cluster = MongoClient('mongodb://127.0.0.1:27017/')

db = cluster['socialApp']
users = db['users']
posts = db ['posts']
comments = db['comments']

app = Flask(__name__)
CORS(app)
app.secret_key = '3456789'

@app.route('/')
def ho():
    return redirect('/login')

@app.route('/login')
def home():
    return render_template('login.html')

@app.route('/account/login',methods=['POST'])
def auth():
    email = request.form['email']
    password = request.form['password']
    user = users.find_one({"email":email})
    if user and password == user['password']:
       session['email'] = email
       return redirect('/dashboard')
    return redirect('/login')
    
@app.route('/register')
def sign():
    return render_template('signup.html')

@app.route('/account/create',methods=['POST'])
def reg():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    try:
        user = users.find_one({"email":email})
        if user:
            return render_template('signup.html',status='User already exist')
        users.insert_one({"email":email,"name":name,"password":password})
    except:
        return render_template('signup.html',status="Something went wrong...")
    return render_template('signup.html',status="Account Created...")

@app.route('/upload',methods=['POST'])
def upload():
    try:
        email = session['email']
        title = request.form['postTitle']
        post = request.files['post']
        description = request.form['description']
        s3.upload_fileobj(post,'end.to.end',post.filename)
        posts.insert_one({"useremail":email,"post":post.filename,"description":description,"title":title})
    except:
        return render_template('createpost.html',status="Something went wrong...")

    return render_template('createpost.html',status="Post uploaded successfully")

@app.route('/dashboard')
def dash():
    try:
        feed = posts.find()
        urls = [ ]
        for i in feed:
            urls.append({"url":
                s3.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={
                    "Bucket":'end.to.end',
                    "Key":i['post']
                    },
                    ExpiresIn=3600
                ),
                "desc":i['description'],
                "email":i['useremail'],
                "_id":i['_id']
            })
        return render_template('dashboard.html',data = urls )
    except Exception as e:
        return "Some thing went"

@app.route('/myposts')
def my():
    try:
        email = session['email']
        myfeed = posts.find({"useremail":email}) 
        keys = [{"key":i['post'],'desc':i['description']} for i in myfeed]
        urls = [ ]
        for i in keys:
            urls.append({"url":
                s3.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={
                        "Bucket":'end.to.end',
                        "Key":i['key']
                    },
                    ExpiresIn=3600
                ),
                "desc":i['desc']
            })
        return render_template('myposts.html',data = urls )
    except:
        return redirect('/login')
    
@app.route('/postcomment',methods=['POST'])
def postcomment():
    #session['email']
    body = request.get_json()
    comments.insert_one({"postid":body['postid'],"comment":body['comment']})
    return {"message":"Comment Updated to this post"+body['postid']}

@app.route('/createpost')
def creatr():
    try:
        session['email']
        return render_template('createpost.html')
    except:
        return redirect('/login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/comments',methods=['post'])
def data():
    body = request.get_json()
    d = list(comments.find({"postid":body['id']}))
    for i in d:
        i['_id'] = str(i['_id'])
    return jsonify(d)

@app.route('/analysis',methods=['post'])
def analasis():
    body = request.get_json()
    comme = comments.find({"postid":body['postid']})
    comments_list = [ ]
    for i in comme:
        comments_list.append(i['comment'])
    res = comprehend.batch_detect_sentiment(TextList=comments_list,LanguageCode = 'en')
    sentiments = []
    for i in res['ResultList']:
        sentiments.append(i['Sentiment'])
    return {"postive":sentiments.count('POSITIVE'),"negative":sentiments.count('NEGATIVE'),"neutral":sentiments.count('NEUTRAL')}

if __name__ =="__main__":
    app.run(host='0.0.0.0',port=5000)