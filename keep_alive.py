from flask import Flask, render_template
from threading import Thread
from replit import db
from updateData import getData, getToken
from iso import collectISOinList
from vcbot import collectVoteHistory, formatRetrospectiveVCWebsite, updateVoteHistory
from flask import request, redirect
import os


class post:  #object to store post data

  def __init__(self, user, number, text_rendered, text_bbcode, id, date):
    self.user = user
    self.number = number
    self.text_rendered = text_rendered
    self.text_bbcode = text_bbcode
    self.id = id
    self.date = date


class vote:  #object to store vote data

  def __init__(self, player, target, url, postnum):
    self.player = player
    self.target = target
    self.url = url
    self.postnum = postnum


app = Flask('')


@app.route('/')
def home():
  return ("I'm alive!")


@app.route("/restart")
def restart():
  return render_template("restart.html")


@app.route("/restart_now")
def restart_now():
  import os
  os.system("kill 1")
  return ("Restarted")


@app.route("/db_url", methods=['POST'])
def return_url():

  api_key = request.form['key']

  if api_key == getToken('db_key'):
    print("Valid request for url made.")
    return (
      "https://kv.replit.com/v0/eyJhbGciOiJIUzUxMiIsImlzcyI6ImNvbm1hbiIsImtpZCI6InByb2Q6MSIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJjb25tYW4iLCJleHAiOjE3MTk3MjI2MzcsImlhdCI6MTcxOTYxMTAzNywiZGF0YWJhc2VfaWQiOiJjNmNiNWJmZS0zOGM5LTRkNGEtYTU5ZC1hMWFhODdiNGZiNmMiLCJ1c2VyIjoicnlhc3Q4OSIsInNsdWciOiJPcmJpdC1FcHNpbG9uIn0.IY7RGVYAquVZ6vz5k-yFCsjAQsoKyFuYHHmYLV_7RZxxF4UYnMbQCg-YMThPsqEl6c0gWIwe-Y0aAq-xlqJqvg"
    )
  else:
    print("Error - invalid db url request made")
    return ("Error - check the key.")


@app.route('/legacy/<game>/<target>')
def targetiso(game, target):

  print("getting posts...")
  posts = collectISOinList(game, target, lowerbound=-1, upperbound=100000)
  print("got posts")
  print(len(posts))
  posts_edited = []

  for comment in posts:
    i = 0
    text_bbcode = """[QUOTE="{}, post: {}, member: 1"]{}[/QUOTE]\n""".format(
      comment[0], comment[3], comment[2])
    while (text_bbcode.find("""<aside class="quote">""") != -1):
      print("found quote")
      tag1 = text_bbcode.find("""<aside class="quote">""")
      tag2 = text_bbcode.find("</aside>")
      text_bbcode = text_bbcode.replace(text_bbcode[tag1:tag2 + 8], "")
      i = i + 1
      if (i > 100):
        print("Stuck in quotes loop")
        # print(comment[2])
        break

    posts_edited.append(
      post(comment[0], str(comment[1]), comment[2], text_bbcode,
           str(comment[3]), comment[4]))

  print("Rendering")
  return render_template('targetiso.html',
                         url=getData("url" + game) + "post-",
                         target=target,
                         posts=posts_edited,
                         gameletter=game)


@app.route('/<game>/<target>')
def targetisonew(game, target):
  print("getting posts...")
  posts = collectISOinList(game, target, lowerbound=-1, upperbound=100000)
  print("got posts")
  print(len(posts))
  articles = []
  for comment in posts:
    articles.append(comment[5])

  print("Rendering")
  return render_template('targetisonew.html', posts=articles)


@app.route('/<game>/updateVotes')
async def updateVC(game):
  print("updating votecount...")
  await updateVoteHistory(game)
  return redirect("/" + game + "/votecount")


@app.route('/<game>/votecount/<postnum>')
def ret_votecount(game, postnum):
  print("getting VC...")
  vc = formatRetrospectiveVCWebsite(game, int(postnum))
  print("got vc")
  print(vc)
  return render_template('votecount.html', text=vc)


@app.route('/threads/<thread>/<post>')
def thread(thread, post):
  return redirect("https://www.hypixel.net/threads/" + str(thread) + "/" +
                  str(post))


@app.route('/<game>/votecount')
def votecount(game):
  print("getting VC...")
  vc = formatRetrospectiveVCWebsite(game, int(30000))
  print("got vc")
  print(vc)
  return render_template('votecount.html', text=vc)


@app.route('/goto/<path:rest>')
def goto(rest):
  query_string = request.query_string.decode("utf-8")
  redirect_url = f"https://www.hypixel.net/goto/{rest}"
  if query_string:
    redirect_url += f"?{query_string}"
  return redirect(redirect_url)


@app.route('/<game>/votes')
def votehistorynew(game):
  print("getting votes...")
  votes = collectVoteHistory(game, firstPost=-1, lastPost=200000)
  print("got votes")
  print(len(votes))
  votelist = []
  for votePlaced in votes:
    votelist.append(
      vote(votePlaced[0], votePlaced[1], votePlaced[2], str(votePlaced[3])))

  print("Rendering")
  return render_template('votehistory.html', votes=votelist)


def run():
  app.run(host='0.0.0.0', port=8080)


def keep_alive():
  t = Thread(target=run)
  t.start()


keep_alive()
