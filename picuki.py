#!/usr/bin/python
# picuki.com ,url post grabber / downloader © 2021.04 dtz-aditia
import requests, json, bs4, os, tqdm, zipfile
from urllib.parse import parse_qs, urlparse

class Picuki(object):
	def __init__(self):
		self.session = requests.Session()
		self.session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36 OPR/67.0.3575.137"
		self.BASE = "https://www.picuki.com"
		self.MORE = True
		self.IDPOST = []
		self.PEOPLE = {
			"username": "",
			"full_name": "",
			"profile_pict": "",
			"images": [],
			"videos": [],
			"total_posts": ""
		}

	def compressFile(self):
		#https://stackoverflow.com/questions/47438424/python-zip-compress-multiple-files/47440162
		usernames = self.PEOPLE["username"].removeprefix("@")
		path = f"/storage/emulated/0/picuki/{usernames}/"
		zp = zipfile.ZipFile(f"{path}{usernames}.zip", mode="w")
		for filename in os.listdir(path):
			if (filename.split('.')[-1] in ["jpg","mp4"]):
				zp.write(
					path + filename, filename, compress_type=zipfile.ZIP_DEFLATED)
				os.remove(path + filename)
			else:
				continue
		zp.close()
		print(f' + Archive saved as -> {usernames}.zip')

	def download(self, **kwargs):
		d = {}
		base_dir = f"/storage/emulated/0/picuki/{self.PEOPLE['username'].strip('@')}/"
		if (url := kwargs.get("url")):
			d["url"] = url
			d["filename"] = urlparse(url).path.split('/')[-1]
			if (dirs := kwargs.get("dirs")):
				d["local_dirs"] = dirs
			else:
				while (True):
					if not os.path.exists(base_dir):
						try:
							os.makedirs(base_dir)
						except PermissionError:
							print(" + Please give me permission to acces your storage :) !")
							os.system("termux-setup-storage")
							continue
					else:
						break
				d["local_dirs"] = base_dir
		contents = self.session.get(d["url"], stream=True)
		progs = tqdm.tqdm(
			total=int(contents.headers.get("content-length",0)),
			unit="B",
			unit_scale=True)
		with open(d["local_dirs"] + d["filename"], "wb") as f:
			for content in contents.iter_content(1024):
				progs.update(
					len(content))
				f.write(content)
		progs.close()
		print(f" + (saved) as -> {d['filename']}")

	def parse(self, responseText):
		responseText = responseText.text if hasattr(responseText, "text") else responseText
		return bs4.BeautifulSoup(responseText, "html.parser")

	def decodeUrl(self, url):
		if url.startswith("/app/"):
			return parse_qs(urlparse(url).query)["url"][0]
		else:
			ps = parse_qs(urlparse(url).path)
			if "/hosted-by-instagram/url" in list(ps.keys()):
				return ps["/hosted-by-instagram/url"][0].replace('||','/')
			else:
				return None

	def getID(self, user):
		if not user.startswith("/app/"):
			page = self.session.get(self.BASE + f'/profile/{user}')
			soup = self.parse(page)
			if (info := soup.find(class_="profile-info")):
				u = info.text.strip().split('\n')
				self.PEOPLE["username"] = u[0]
				self.PEOPLE["full_name"] = u[1]
				self.PEOPLE["total_posts"] = soup.find(class_="total_posts").text
				if (pp := info.find('img')):
					self.PEOPLE["profile_pict"] = self.decodeUrl(pp.attrs['src'])
				else:
					pass
			else:
				pass
		else:
			page = self.session.get(self.BASE + f"/profile/{self.PEOPLE['username'].strip('@')}{user}")
		soup = self.parse(page)
		if (media := soup.find_all("div", {"data-s":"media"})):
			for x in media:
				self.IDPOST.append(
					x.a.attrs.get("href"))
				print(f" + {self.IDPOST[-1]}")
				print(f" + {len(self.IDPOST)} POST RETREVIED \r", end="")
			if (next := soup.find(class_='load-more-wrapper')):
				if (more_page := next.attrs.get("data-next")):
					return self.getID(more_page)
				else:
					self.MORE = False
			else:
				self.MORE = False
		else:
			exit(" + People Not Found, check again your username!")

	def getMedia(self, posturl):
		VIDEOS = []
		IMAGES = []
		THUMBNAIL = []
		page = self.session.get(posturl)
		soup = self.parse(page)
		if (desc := soup.find(class_="single-photo-description")):
			if (video := soup.find_all('video')):
				for v in video:
					THUMBNAIL.append(
						self.decodeUrl(v.attrs.get('poster')))
					VIDEOS.append(
						self.decodeUrl(v.source.attrs.get("src")))
			elif (image := soup.find_all('img', id="image-photo")):
				for i in image:
					IMAGES.append(
						self.decodeUrl(i.attrs.get('src')))
			if len(IMAGES) != 0:
				return {
					"t": desc.text,
					"images": IMAGES}
			elif len(VIDEOS) != 0:
				return {
					"t": desc.text,
					"thumbnail": THUMBNAIL,
					"videos": VIDEOS}
			else:
				return False

	def __Main__(self, username, dlimgs=False, dlvideos=False, dlthumbnails=False, compress=False):
		self.getID(username)
		if not self.MORE:
			if len(self.IDPOST) != 0:
				for x, j in enumerate(self.IDPOST, 1):
					print(f" + ({x}) of ({len(self.IDPOST)}) -> {j.split('/')[-1]}")
					if (media := self.getMedia(j)):
						if (thisimg := media.get('images')):
							self.PEOPLE['images'].append(
								media)
						elif (thisvideo := media.get('videos')):
							self.PEOPLE['videos'].append(
								media)
					else:
						continue
				ask = input(f" + {len(self.PEOPLE['images'])} Images and {len(self.PEOPLE['videos'])} Videos Retrevied, Download all ? (y/n) -> ").lower()
				if ask == "y":
					if dlimgs is True:
						print(f" + Downloading all images from user -> {self.PEOPLE['full_name']}")
						for k, v in enumerate(self.PEOPLE['images'], 1):
							print(f" + ({k}) of ({len(self.PEOPLE['images'])}) Images")
							for i in v['images']:
								self.download(url=i)
					if dlvideos is True:
						print(f" + Downloading all videos from user -> {self.PEOPLE['full_name']}")
						for k, v in enumerate(self.PEOPLE['videos'],1):
							print(f" + ({k}) of ({len(self.PEOPLE['videos'])}) Videos")
							for i in v['videos']:
								self.download(url=i)
					if dlthumbnails is True:
						print(f" + Downloading all thumbnail videos from user -> {self.PEOPLE['full_name']}")
						for k, v in enumerate(self.PEOPLE['videos'], 1):
							print(f" + ({k}) of ({len(self.PEOPLE['videos'])}) Thumbnail Videos")
							for i in v['thumbnail']:
								self.download(url=i)
					if compress is True:
						return self.compressFile()
				else:
					with open('result.json','w') as f:
						f.write(str(self.PEOPLE))
					print(f' + all done with {len(self.IDPOST)} url post')
			else:
				print(' + line 166')

if __name__=="__main__":
	dlimgs = False
	dlvideos = False
	compress = False
	dlthumbnails = False
	try:
		print("""
 it is recommended to use a WiFi network 
 if you find a lot of posts,
 the results will be saved on internal storage.

 report -> https://t.me/aditia_dtz
""")
		username = input(" + username (without @) : ")
		if username != '' and not username.startswith("@"):
			c = input(" + Download all videos -> (y/n) : ").lower()
			if c == "y":
				dlvideos = True
			c = input(" + Download all images -> (y/n) : ").lower()
			if c == "y":
				dlimgs = True
			c = input(" + Download all thumbnail videos -> (y/n) : ").lower()
			if c == "y":
				dlthumbnails = True
			c = input(" + Commpress all files after download ? -> (y/n) : ").lower()
			if c == "y":
				compress = True
			Picuki().__Main__(
				username, dlimgs=dlimgs, dlvideos=dlvideos, dlthumbnails=dlthumbnails, compress=compress)
		else:
			exit(f" + Invalid username -> {username}")
	except Exception as e
		exit(str(e))
