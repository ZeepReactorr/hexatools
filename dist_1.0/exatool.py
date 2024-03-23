from bs4 import BeautifulSoup as soup
import requests as req
import PyPDF2
from io import BytesIO
from matplotlib.pyplot import figure
import os
import re
import sys
import numpy as np
from matplotlib import pyplot as plt
import urllib.request as ul
import streamlit as st

#change into the desired directory to store the results of the sorting
dir_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(dir_path)

def sci(keywords):    
    #initialization of variables
    signal = 1
    keywords = ['NULL'] + keywords
    dico_keywords = {i:0 for i in keywords}
    
    #Opens the document outputed from link_retriever.py
    F = open('Results.txt', 'r', encoding='utf-8')
    for num, line in enumerate(F.readlines()):
        limite = num + 1
    F.close()
    
    F = open('Results.txt', 'r', encoding='utf-8')

    #Opens output file
    Searched_material = open('Searched_material.txt', 'w', encoding='utf-8')
    count_bad_links = 0
    number = 0
    textbar = "Searching keywords..."
    bar_articles = st.progress(0, text=textbar)

    #loop through each lines of the file with a link in each
    for i in F.readlines(): 
        #process the line to obtain a viable DOI
        i = i.strip('\n')
        i = i.split('\t')

        #indicates progression of the program
        bar_articles.progress(np.round((signal/limite), 2), text=textbar)
        signal+=1
                
        #rebuild the link to the full article
        link = 'https://doi.org/' + i[0]
        date = i[1]
        
        #retrieve data through the DOI. If an error occurs, we switch to the next article
        try :
            retrieved_data = req.get(link)
            my_raw_data = retrieved_data.content
        except Exception:
            count_bad_links +=1
            continue
        
        output = ''
        #if the DOI redirect toward a PDF, the text is extracted from it in this code
        if b'%PDF' in my_raw_data:
            data = BytesIO(my_raw_data)
            try :
                read_pdf = PyPDF2.PdfReader(data)
                for page in range(len(read_pdf.pages)):
                    txt = read_pdf.pages[page].extract_text()
                    txt = txt.encode('UTF-8', errors = 'ignore')
                    output = str(txt.strip())                
            except Exception:
                pass
        
        #filter the CSS and html beacons out of the file             
        else:
            db_txt = soup(my_raw_data, "html.parser")
            txt = db_txt.find_all(string = True)
            blacklist = [
                '[document]',
                'noscript',
                'header',
                'html',
                'meta',
                'head', 
                'input',
                'script',
                'footer',
                'style',
                ]

            for t in txt:
                if t.parent.name not in blacklist:
                    output += '{}'.format(t)

            if len(output) < 1000:
                count_bad_links+=1
                continue
            else:
                number+=1
                
            
            output = re.sub("\n|\r|\rn", '', output) 
            output = output[output.find('Abstract'):]
            output = str(output[:output.find('References')]).lower()            
                        
        #write the link in the output document if the conditions are fullfilled : if it is exactly the desired material.        
        dico = {keywords[i]:output.count(keywords[i].lower()) for i in range(0, len(keywords))}
        dico_keywords[max(dico, key=dico.get)] += 1
        Searched_material.write(link + '\t' + date + '\t' + str(max(dico, key=dico.get)) + '\n')
        dico = {}
                
    for key, res in dico_keywords.items():
        print(key, res)

    #Summarize the results in the console to give a preview of the results
    st.markdown(f'full text retrieved : {number}\t impossible links to retrieve : {count_bad_links}')
    F.close()
    return 'Done'

#print(sci(["Illumina", "Nanopore"]))

def tendency(keywords, date_range):
    #open results files
    results = open('Searched_material.txt', 'r', encoding='utf-8')

    #Initialize the dates to position the temporality of the articles
    dates = [i for i in range(int(date_range[0]), int(date_range[1]))]

    #Process the data in list containing only the date in which the articles were written
    list_material_date = [(i.split('\t')[1].strip('\n'),i.split('\t')[2].strip('\n')) for i in results.readlines()]
    
    #Count each date occurence as each article has an associated publication date. Thus number of date = number of articles
    count_dates = {i:[int(j[0]) for j in list_material_date if j[1] == i] for i in keywords}

    dec = 0
    fig = figure(figsize=(11, 5))
    for i in count_dates:
        res = [count_dates[i].count(j) for j in dates]
        dates = [i+dec for i in dates]
        plt.bar(dates, res, label=i, width = 0.4, alpha=0.2)
        plt.xlabel('time')
        plt.ylabel('number of publications')
        plt.title(f'Global distribution of the publications between {date_range[0]} and {date_range[1]}')
        dec += 0.25
    

    plt.legend()
    plt.savefig('plot.png')
    results.close()

def dl_intel(url, pure_url):
    #Initializing variables
    responseTxt_4 = ''
    
    #Opening links to articles used to trim the HTML data
    DOI_trash = []
    
    #Obtain HTML data
    client = req.get(url)
    htmldata = client.text
    client.close()
    
    #this part finds the data we look for thanks to HTML beacons, here we want to find the PMID because an article link is always in the form https://pubmed.ncbi.nlm.nih.gov/<PMID>
    db = soup(htmldata, "html.parser")
    locator = db.findAll('a', {'class':'docsum-title'}, href = True)  
    locator_2 = re.findall(r'(?<=href="/)\w+', str(locator))
    links = [i for i in locator_2]
    
    #reforge the url and store it in a new list
    clean_links = [str(pure_url + str(i.strip()) + '/') for i in links]

    for i in clean_links:        
        #We can now use the reforged URL to access each article in the webpage
        site_2 = ul.Request(i)
        client_2 = ul.urlopen(i)
        htmldata_2 = client_2.read()
        client_2.close()
        
        db_2 = soup(htmldata_2, "html.parser")
        
        #Here we locate each element we need to retrieve and store it. Since some caracters used in the articles are not understood we explicitely encode them in UTF-8.
        locator_date = db_2.findAll('span', {'class':'cit'})
        try :
            date = str(re.findall("\d{4}", str(locator_date))[0])
        except :
            continue
        
        locator_4 = db_2.findAll('a', {'class':'id-link'})
        for n in locator_4:
            responseTxt_4 = n.text.encode('UTF-8')
        responseTxt_4 = str(responseTxt_4.strip())
        responseTxt_4 = responseTxt_4[2:-1]
        
        #Store the DOI of the articles and the date they were written
        DOI_trash.append(f"{responseTxt_4}\t{date}\n")
    
    return DOI_trash

#print(dl_intel('https://pubmed.ncbi.nlm.nih.gov/?term=mitochondria&page=1', 'https://pubmed.ncbi.nlm.nih.gov/'))

#This function's sole purpose is to pass to the next page in PubMed. It is possible to set a limit to how many pages you want to collect the articles' link from.
def switch_page(url, pure_url):
    #find the limit number of pages to go through
    client = req.get(url)
    htmldata = client.text
    client.close()
    db = soup(htmldata, "html.parser")
    locator = db.findAll('span', {'class':'value'})  

    nb_articles = ''.join(re.findall('[0-9]+', str(locator[0])))
    limite = (int(nb_articles)//10)+1
    if limite > 100:
        limite = 100
    count = 1
    link = url
    
    #Open our definitive file
    Results = open('Results.txt', 'w')

    textbar = "Retrieving articles..."
    bar_retrieval = st.progress(0, text=textbar)
    
    while count <= limite :
        K=dl_intel(link, pure_url)
        print(f"{np.round((count/limite)*100)}%")
        bar_retrieval.progress(np.round((count/limite), 2), text=textbar)
        link = url + '&page=' + str(count)
        count+=1
        for lines in K:
            Results.write(lines)
    st.write(f'{nb_articles[0]} articles retrieved !\n')
    return ''

#print(switch_page('https://pubmed.ncbi.nlm.nih.gov/?term=oxyrrhis+sequencing&filter=simsearch2.ffrft&filter=years.2010-2024', 'https://pubmed.ncbi.nlm.nih.gov/'))

