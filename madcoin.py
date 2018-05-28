# EngHack 2018: CoinWatch
# a program to analyze initial coin offering (ICO) websites for potential fraud or risk
# generates a JSON file which is then used in a web app

import requests, bs4, PyPDF2, itertools, random, json
from textblob import TextBlob
from textblob.tokenizers import WordTokenizer, SentenceTokenizer

def check_pairs(lst, words, weight):
    global cred_score
    for word1, word2 in lst:
        for i in range(len(words)):
            if word1 == words[i]:
                if word2 in words[max(0, i-3):min(i+4, len(words))]:
                    cred_score -= weight
                    output['language'] -= weight
                    return  
def plagiarism_check(reader, pdfurl):
    global cred_score
    text = ''
    for i in range(5, reader.numPages):
        text += reader.getPage(i).extractText()
    sentences = TextBlob(text, tokenizer=SentenceTokenizer())
    sentences = [' '.join(sentence.split()) for sentence in sentences]
    sentences = [sentence for sentence in sentences if len(sentence) > 50]
    t = random.sample(sentences, min(len(sentences), 3))  # can increase this number
    for sentence in t:
        print(sentence)
        res = requests.get('https://www.google.ca/search?q="' + sentence + '"')
        soup = bs4.BeautifulSoup(res.text, 'html.parser')
        results = soup.select('h3.r a')
        for result in results[:min(len(results), 3)]:  # can increase this number
            if results.get('href') != pdfurl:
                cred_score -= 0.05
                output['plagiarism'] = -0.05
                return
def icorating():
    global cred_score
    try:
        res = requests.get('https://www.google.ca/search?q="' + coin + '"%20site:icorating.com')  
    except:
        return  # need to resolve this
    soup = bs4.BeautifulSoup(res.text, 'html.parser')
    results = soup.select('h3.r a')
    if results == []:
        return
    href = results[0].get('href')
    if href.startswith('/'):
        try:
            href = href[href.index('http'):]
        except:
            return   # need to resolve this
    res = requests.get(href)
    soup = bs4.BeautifulSoup(res.text, 'html.parser')
    lst = soup.select('div.right-block')
    if lst == []:
        return
    text = lst[0].getText()
    blob = TextBlob(text)
    if blob.objectivity < 0.5 and blob.polarity < 0:
        cred_score -= 0.05
        output['review'] = -0.05
            
output_template = {'online_presence':0, 'github':0, 'linkedin':0, 'partners':0, 'language':0,
                'terms':0, 'plagiarism':0, 'whitepaper_short':0, 'whitepaper_missing_info':0,
                'whitepaper':0, 'roadmap':0, 'review':0, 'score':0}
final_collection = {}
ico_res = requests.get('https://tokenmarket.net/ico-calendar')  # getting list of coins from here
ico_soup = bs4.BeautifulSoup(ico_res.text, 'html.parser')
ico_lst = ico_soup.select('td.col-asset-name div a')
for k in range(len(ico_lst)):
    cred_score = 1.0  # perfect score
    output = output_template.copy()
    ico_res2 = requests.get(ico_lst[k].get('href'))
    ico_soup2 = bs4.BeautifulSoup(ico_res2.text, 'html.parser')
    coin = ico_soup2.select('h1')[0].getText().strip().lower()
    url = ico_soup2.select('div.asset-buttons a[class="btn btn-primary btn-block btn-lg"]')[0].get('href')
    try:
        res = requests.get(url)
        res.raise_for_status()
    except:
        print('Connection to %s failed (bad HTTP request).' % url)
        continue
    soup = bs4.BeautifulSoup(res.text, 'html.parser')
    if soup.select('body') == [] or len(list(soup.select('body')[0].descendants)) < 30:
        print('Connection to %s failed (JavaScript required).' % url)  # need to resolve this
        continue
    print('Current coin: %s' % coin)

### ONLINE PRESENCE
    alst = soup.select('a')
    social_media_score = 0
    social_media = ['https://t.me', 'https://twitter.com', 'https://facebook.com', 'https://medium.', 'https://www.youtube.com', 
                    'https://www.instagram.com', 'https://bitcointalk.org', 'https://www.reddit.com']
    hrefs = [elem.get('href') for elem in alst]
    for media in social_media:
        for href in hrefs:
            if href is not None and media in href:
                social_media_score += 1
                break
    if social_media_score < 3:
        cred_score -= 0.05
        output['online_presence'] = -0.05

## GITHUB REPO
    have_github = False
    for href in hrefs:
        if href is not None and 'https://github.com' in href:
            # NEED TO VERIFY THAT THE GITHUB REPO IS LEGITIMATE
            have_github = True
            break  # should consider case when there's more than one GitHub link
    if not have_github:
        cred_score -= 0.08
        output['github'] = -0.08 

### TEAM MEMBERS
    bodytext = soup.select('body')[0].getText().lower()
    linkedin_count = 0
    for href in hrefs:
        if href is not None and 'https://www.linkedin.com' in href:
            linkedin_count += 1  # need to prevent this from including the company LinkedIn
    if linkedin_count < 6:
        cred_score -= 0.03
        output['linkedin'] = -0.03
        position_count = 0
        positions = [('ceo', 'founder'), ('cmo', 'marketing', 'pr'), ('team lead', 'manager'),
                     ('cfo', 'chief financial officer', 'financial advisor', 'financial analyst'), 
                     ('developer', 'development'), ('engineer',)]
        for group in positions:
            for position in group:
                if position in bodytext:
                    position_count += 1
                    break
        if position_count < 6:
            cred_score -= 0.08
            output['team'] = -0.08

### PARTNERS/INVESTORS
    if 'partners' not in bodytext and 'investors' not in bodytext:
        cred_score -= 0.07
        output['partners'] = -0.07

### LANGUAGE             
# root words only
    guarantee_words = ['guarantee', 'fixed', 'periodic', 'regular', 'permanent', 'steady', 'promise', 'assur', 'always']
    profit_words = ['profit', 'return', 'payout', 'earnings', 'income', 'interest', 'revenue', 'yield']
    hype_words = ['revolution', 'huge', 'incredible', 'unbelievable' 'safest', 'simplest', 'best' 'totally', 'perfect', 'immediate']
    danger_pairs = [('never','worry'), ('always','safe')]
    # should use machine learning to come up with a list of synonyms of these words
    blob = TextBlob(bodytext, tokenizer=WordTokenizer())
    words = blob.tokens
    check_pairs(itertools.product(guarantee_words, profit_words), words, 0.1)
    # a phrase along the lines of "guaranteed profits" is flagged
    check_pairs(danger_pairs, words, 0.03)  # these "hype" words is flagged
    check_pairs(zip(hype_words, ['']*len(hype_words)), words, 0.05)
    # a phrase along the lines of "never worry" or "always safe"is flagged

### LEGAL INFORMATION
    if not ('terms & conditions' in bodytext or 'terms and conditions' in bodytext or 'terms of use' in bodytext):
        cred_score -= 0.03
        output['terms'] = -0.03

### WHITEPAPER
    have_whitepaper = False
    have_roadmap = False
    for elem in alst:
        innerText = elem.getText().lower().replace(' ','')
        if 'paper' in innerText:
            have_whitepaper = True
            href = elem.get('href')
            if href is not None and href.endswith('.pdf'):
                if href.startswith('./'):
                    pdfurl = url + href[1:]
                elif href.startswith('/'):
                    pdfurl = url + href
                elif not href.startswith('http'):
                    pdfurl = url + '/' + href
                else:
                    pdfurl = href
                try:
                    res2 = requests.get(pdfurl)
                except Exception as err:
                    break  # need to resolve this
                fo = open('whitepaper.pdf', 'wb')
                for chunk in res2.iter_content(2000000):
                    fo.write(chunk)
                fo.close()
                fi = open('whitepaper.pdf', 'rb')
                try:
                    reader = PyPDF2.PdfFileReader(fi)
                except:
                    fi.close()
                    break  # need to resolve this
                n = reader.numPages
                if n < 9:  # can change this number
                    cred_score -= 0.03
                    output['whitepaper_short'] = -0.03
                subtitle_score = 0
                for i in range(0, min(n, 4)):
                    text = reader.getPage(i).extractText().lower()
                    subtitles = [('roadmap', 'timeline', 'calendar'), ('team',), ('strategy', 'model', 'structure'), 
                                 ('market', 'analysis',)]
                    for j in range(len(subtitles)):
                        for subtitle in subtitles[j]:
                            if subtitle in text:
                                subtitle_score += 1
                                if j == 0:
                                    have_roadmap = True
                                break
                if subtitle_score < 4:
                    cred_score -= 0.05
                    output['whitepaper_missing_info'] = -0.05
                plagiarism_check(reader, pdfurl)
                fi.close()
            else:
                break  # need to resolve this
            break
    if not have_whitepaper:
        cred_score -= 0.2
        output['whitepaper'] = -0.2

### ROADMAP
    if not have_roadmap:
        for heading in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a']:
            lst = soup.select(heading)
            for elem in lst:
                s = elem.getText().lower()
                if s.startswith('roadmap') or s.startswith('timeline') or 'calendar' in s:
                    have_roadmap = True
                    break
            if have_roadmap:
                break
    if not have_roadmap:
        cred_score -= 0.1
        output['roadmap'] = -0.1

### 3RD PARTY OPINION
    icorating()  # using icorating.com as a 3rd-party opinion site; can add more websites later
    
### FINAL CREDIBILITY SCORE
    output['score'] = cred_score
    final_collection[coin] = output

file = open('data.json', 'w')
file.write(json.dumps(final_collection))
file.close()
