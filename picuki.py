#!/usr/bin/python
"""
last update : Sun Apr 24 05:47:24 WIB 2022
limit ? : i don't know.
"""
import requests, tqdm, re, os
from bs4 import BeautifulSoup

class Picuki(object):
	def __init__(self):
		self.host = "https://www.picuki.com"
		self.session = requests.Session()
		self.session.headers.update({
			"Host": self.host.removeprefix("https://"),
			"user-agent":"Mozilla/5.0 (Linux; Android 8.1.0; M5 Build/O11019;) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/100.0.4896.79 Mobile Safari/537.36",
			"accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
			"x-requested-with":"XMLHttpRequest",
			"accept-language":"en-GB,en;q=0.9,id-ID;q=0.8,id;q=0.7,en-US;q=0.6"
		})
		self.video = False
		self.image = False
		self.thumbnail = False
		self.dImg = 0
		self.dVid = 0
		self.dThum = 0
		self.username = None

	def parseBs4(self, raw):
		raw = raw.text if hasattr(raw, "text") else raw
		return BeautifulSoup(raw, "html.parser")

	def validateUsername(self, user) -> str:
		if user.strip() and not user.startswith('@'):
			return True
		return False

	def searchUser(self, username):
		if self.validateUsername(username):
			self.session.headers["referer"] = self.host
			page = self.parseBs4(self.session.get(f"{self.host}/search/{username}").text)
			if (als := page.findAll(class_="result-username")):
				self.session.headers["referer"] = f"{self.host}/search/{username}"
				for i in als:
					yield i.text.strip()
			return False
		return False

	def getInfo(self, page):
		if isinstance(page, str):
			if (info := re.search(r"(?<=name-top\">)(?P<username>[^>].*?)(?=</h1>)[\s\S]*?(?<=name-bottom\">)(?P<full_name>[^>].*?)(?=</h2>)[\s\S]*?(?<=description\">)\s+(?P<bio>[^>].*?)\s+(?=</div>)[\s\S]*?(?<=total_posts\">)(?P<total_posts>[\d+].*?)(?=</)[\s\S]*?(?<=followed_by\">)(?P<followers>[^>].*?)(?=</)[\s\S]*?(?<=follows\">)(?P<following>[^>].*?)(?=</)",page)):
				return info.groupdict()
			return False
		elif isinstance(page, BeautifulSoup):
			if page.find(class_="profile-info"):
				return dict(zip(
					('username', 'full_name',
						'bio', 'total_posts',
						'followers', 'following'),
					(l.find(class_=i).text.strip() for i in (
						"profile-name-top","profile-name-bottom",
						"profile-description","total_posts",
						"followed_by","follows"))
					))
			return False

	def getMediaId(self, page):
		if isinstance(page, str):
			if (mid := re.findall(r"<a\s+href\=\"http[s]:\/\/www\.picuki\.com\/media\/([\d+].*?)\"",page)):
				self.getMedia(mid)
				self.count += len(mid)
				if (next := re.search(r"(\/app\/controllers\/ajax[^'].*?)\"",page)):
					self.getMediaId(self.session.get(self.host + next.group(1)).text)
				return True
			return False
		elif isinstance(page, BeautifulSoup):
			if (mid := page.findAll("div",{"data-s":"media"})):
				mid = [i.a.attrs.get('href').split('/')[-1] for i in mid]
				self.count += len(mid)
				self.getMedia(mid)
				if (next := page.find(class_="load-more-wrapper")):
					self.getMediaId(
						self.session.get(
							self.host + next.attrs["data-next"]).text)
				return True
			return False

	def download(self, filename, url):
		path = f"/storage/emulated/0/picuki/{self.username}"
		while True:
			try:
				if not os.path.exists(path):
					os.mkdir(path)
				else:
					break
			except PermissionError:
				print("  • ! please give me permission!")
				continue
		contents = requests.get(url, stream=True)
		if "Content-Disposition" in contents.headers:
			if (fname := re.search(r"(?<=filename\=\")([^>].*?)(?=\";)",contents.headers['Content-Disposition'])):
				filename = fname.group(1)
		filename = filename.split(".webp")[0] + ".jpg" if filename.endswith('.webp') else filename
		print(f"  •! downloading : {filename}")
		progs = tqdm.tqdm(
			total=int(contents.headers.get("content-length",0)),
			unit="B",
			unit_scale=True)
		with open(f"{path}/{filename}", "wb") as f:
			for content in contents.iter_content(1024):
				progs.update(
					len(content))
				f.write(content)
		progs.close()
		print(f"  • (content saved) :)")

	def getMedia(self, media_id):
		if "referer" in self.session.headers:
			self.session.headers.pop("referer")
		if len(media_id) != 0:
			for k, v in enumerate(media_id, 1):
				print(f"  • ({k}) getting -> {v}")
				page = self.session.get(f"{self.host}/media/{v}").text
				soup = self.parseBs4(page)
				if (info := re.search(r"(?<=photo-nickname\">).*?\">(?P<name>[^>].*?)(?=</)[\s\S]*?(?<=photo-time\">)(?P<time>[^>].*?)(?=</)[\s\S]*?(?<=photo-description\">)(?P<desc>[^>].*?)(?=\s+(<a|</div>))",page)):
					i = info.groupdict()
					if 'href=' in i["desc"]:
						i["desc"] = ', '.join(re.findall(r"(?<=\">)(#[^>].*?)(?=</a>)",page))
				elif (info := soup.find(class_="single-photo-info")):
					i = dict(zip(
						("name","time","desc"),(
							soup.find(class_=i).text.strip() for i in (
								"single-photo-nickname","single-photo-time","single-photo-description"))))
				print("\n".join(f"  • {k.title()} : {v}" for k, v in i.items()))
				print()
				getName = (lambda n: i.get("desc").split('/')[0] if not i.get('desc').strip().startswith("#") else n)
				if (vi := soup.findAll("video")):
					if self.video:
						for iv in vi:
							self.dVid +=1
							self.download(
								getName(f"{v}.mp4"),
							iv.attrs["src"])
					if self.thumbnail:
						for iv in vi:
							self.dThum +=1
							self.download(
								getName(f"{v}.jpg"),
							iv.attrs.get('poster'))
				elif (img := soup.findAll('img')):
					if self.image:
						for im in img:
							self.dImg +=1
							self.download(
								getName(f"{v}.jpg"),
							im.attrs['src'])
				else:
					if (im := re.findall(r"(?<=<img\ssrc=\")(http[s]:\/\/[^>].*?)(?=\"\s)",page)):
						if self.image:
							for im in img:
								self.dImg +=1
								self.download(
									getName(f"{v}.jpg"),
								im.attrs['src'])
					else:
						False
		return False

class Main(Picuki):
	def __main__(self):
		print("""
  ╔═╗┬╔═╗┬ ┬╦╔═┬
  ╠═╝│║  │ │╠╩╗│
  ╩  ┴╚═╝└─┘╩ ╩┴

  •! insta viewer.
  •! made by : github.com/aditia-dgzr
  •! it is recommended to use a WiFi network 
     if you find a lot of posts,
     the results will be saved on internal storage.
""")
		user = input('  • username (without @) : ').strip()
		dImg = input('  • download all images ? (y/n) : ')
		dVid = input('  • download all videos ? (y/n) : ')
		dThumb = input('  • download all thumbnail video? (y/n) : ')
		for i in (dImg,dVid,dThumb):
			if not i.strip() or i not in ('y','n'):
				exit("  • dont blank !")
		self.username = user
		if (use := self.validateUsername(user)):
			print(f"  •! wait search username <{user}>\n")
			if (res := self.searchUser(user)):
				r = list(res)
				print(f"  •! found {len(r)} results : ")
				print("\n".join(f"  {i}). {n} " for i, n in enumerate(r, 1)))
				use = int(input("\n  •! Choice : "))
				if (use - 1) < len(r):
					page = self.session.get(f"{self.host}/profile/{r[use-1].strip('@')}").text
					if (info := self.getInfo(page)):
						print()
						print("\n".join(f"  • {k.title()}: {v}" for k, v in info.items()))
						print()
						print(f"  • fetching all media id")
						if dImg == "y":
							self.image = True
						if dVid == "y":
							self.video = True
						if dThumb == "y":
							self.thumbnail = True
						self.getMediaId(page)
						print(f"  • {self.dImg} image, {self.dVid} video, {self.dThum} thumbnail!")
					else:
						pass
				else:
					pass
			else:
				pass
		else:
			pass

if __name__=="__main__":
	try:
		Main().__main__()
	except Exception as e:
		exit(e)
