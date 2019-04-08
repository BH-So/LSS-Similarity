import psycopg2
import numpy
import nltk
import time
from nltk.corpus import stopwords
import sys

def makeDictionary(fname):
    dic = {}
    f = open(fname, 'r')
    while True:
        line = f.readline()
        if not line: break
        line = line.strip()
        items = line.split('\t')
        l = []
        for item in items[1:]:
            l.append(float(item))
        dic[items[0]] = l
    f.close()
    return dic
 
def is_content(word):
    if word in punctuations:
        return False
    if word in stopwords:
        return False
    return True
 
def getLemmasAndPosTagsData(sentence_id):
    sql_string = "select index, lemma from crowdsourcing.nl_features0 "
    sql_string += "where sentence_id = " + str(sentence_id) + " and index > 0 order by index;"
    curs.execute(sql_string)
    return curs.fetchall()
  
 
def getLemmasAndPosTagsData2(sentence_id):
    sql_string = "select index, lemma from crowdsourcing.sql_features0 "
    sql_string += "where sentence_id = " + str(sentence_id) + " and index > 0 order by index;"
    curs.execute(sql_string)
    return curs.fetchall()
  
 
def getContentWords(words):
    contentWords = []
    for (idx, lemma) in words:
        if is_content(lemma): contentWords.append((idx, lemma))
    return contentWords
  
 
def getSqlAlignedIndices(sql_id, sentence_id):
    sql_string = "select sql_idx from crowdsourcing.alignments where sql_id = " + str(sql_id) + " and sentence_id = " + str(sentence_id) + " group by sql_idx order by sql_idx;"
    curs.execute(sql_string)
    Aligned = set([])
    for (idx, ) in curs.fetchall():
        Aligned.add(idx)
    return Aligned
  
 
def getSentenceAlignedIndices(sql_id, sentence_id):
    sql_string = "select sentence_idx from crowdsourcing.alignments where sql_id = " + str(sql_id) + " and sentence_id = " + str(sentence_id) + " group by sentence_idx order by sentence_idx;"
    curs.execute(sql_string)
    Aligned = set([])
    for (idx, ) in curs.fetchall():
        Aligned.add(idx)
    return Aligned
  
 
def getAlignedNum(Words, alignedIndices):
    count = 0
    for (idx, lemma) in Words:
        if idx in alignedIndices: count += 1
    return count
 
 
def feature_alignment(sql_id, sqlContentWords, sentence_id, sentenceContentWords): 
    sqlAlignedIndices = getSqlAlignedIndices(sql_id, sentence_id)
    sqlAlignedContentNum = getAlignedNum(sqlContentWords, sqlAlignedIndices)
  
    sentenceAlignedIndices = getSentenceAlignedIndices(sql_id, sentence_id)
    sentenceAlignedContentNum = getAlignedNum(sentenceContentWords, sentenceAlignedIndices)
  
    try:
        return float(sqlAlignedContentNum + sentenceAlignedContentNum) / float(len(sqlContentWords) + len(sentenceContentWords))
    except:
        return 0
  
def getContentVector(contentWords):
    count = 0
    contentVector = numpy.zeros(400)
    for (idx, lemma) in contentWords:
        try:
            contentVector = numpy.add(numpy.array(vectorDict[lemma.lower()], dtype='float64'), contentVector)
            count += 1
        except:
            count = count
    if count > 0: return numpy.divide(contentVector, float(count))
    else: return contentVector
  
def feature_distance(sql_pos, sentence_pos):
    return abs(sql_pos - sentence_pos)
 
def feature_vector(sqlContentVector, sentenceContentVector):
    over = numpy.dot(sqlContentVector, sentenceContentVector)
    under = numpy.linalg.norm(sqlContentVector) * numpy.linalg.norm(sentenceContentVector)
    if under != 0: return float(over / under)
    else: return 0
  
def getSqlNl():
#    sql_string = "Select sqi, sei, sqpos, sepos from (select sqi, sei, sqpos, sepos, ui1 from (select u.url_id as ui1, sq.id as sqi, se.position as sqpos from urls.experiment_tb_1 as u, sentences.naive_tb_0 as se, sqls.naive_tb_0_0 as sq where u.url_id = se.url_id and sq.sentence_id = se.id and sq.is_valid = true) as t, (select u1.url_id as ui2, se1.id as sei, se1.position as sepos from urls.experiment_tb_1 as u1, sentences.naive_tb_0 as se1 where u1.url_id = se1.url_id) as t1 where t.ui1 = t1.ui2 order by sei, sqi) as ADF where ui1 in (select SEN.url_id from answers.sql_0_0_nl_0 as ANS join sentences.naive_tb_0 as SEN on ANS.sentence_id = SEN.id);"
    
#    sql_string = "select sq.id, se.id, se.position, se.position from crowdsourcing.sqls as sq, crowdsourcing.sentences as se where sq.sentence_id = se.id;"

    sql_string = "select sqi, sei, sqpos, sepos from (select sq.id as sqi, se.position as sqpos, se.url_id as url_id from crowdsourcing.sqls as sq, crowdsourcing.sentences as se where sq.sentence_id = se.id) as t1, (select se2.id as sei, se2.position as sepos, se2.url_id as url_id from crowdsourcing.sentences as se2) as t2 where t1.url_id = t2.url_id order by sei, sqi;"
    curs.execute(sql_string)
    return curs.fetchall()

if __name__ == "__main__":
    punctuations = ['(','-lrb-','.',',','?',';','_',':','{','}','[','/',']','...','"','\'',')', '-rrb-']
    stopwords = set(stopwords.words('english'))
    stopwords = stopwords - set(['not', 'less', 'under', 'over', 'where', 'above', 'what', 'who', 'or', 'from', 'more', 'and', 'below', 'most', 'which', '\'t'])
    
    conn_string = "host='localhost' dbname='kjhong' user='kjhong' password='kjhong'"
    conn = psycopg2.connect(conn_string)
    curs = conn.cursor()
    
    stime = time.time()
    vectorDict = {}
    vectorDict = makeDictionary('EN-wform.w.5.cbow.neg10.400.subsmpl.txt')
    
    sqlnls = getSqlNl()
    n = int(sys.argv[1])
    num = len(sqlnls) / 32
    if n < 31: sqlnls = sqlnls[n*num : n*num + num]
    else: sqlnls = sqlnls[n*num : ]

#    writeFile = open("features_crowdsourcing_tf.txt", "w")

    csql_id = -1
    csentence_id = -1
    for (sql_id, sentence_id, sql_pos, sentence_pos) in sqlnls:
        if csql_id != sql_id:
            csql_id = sql_id
            sqlWords = getLemmasAndPosTagsData2(sql_id)
            sqlContentWords = getContentWords(sqlWords)
            sqlContentVector = getContentVector(sqlContentWords)
    
        if csentence_id != sentence_id:
            csentence_id = sentence_id
            sentenceWords = getLemmasAndPosTagsData(sentence_id)
            sentenceContentWords = getContentWords(sentenceWords)
            sentenceContentVector = getContentVector(sentenceContentWords)

        insert_query = "insert into crowdsourcing.experiment (sql_id, nl_id, feat1, feat2, feat3) values (" + str(sql_id) + ", " + str(sentence_id) + ", " + str(feature_alignment(sql_id, sqlContentWords, sentence_id, sentenceContentWords)) + ", " + str(feature_distance(sql_pos, sentence_pos)) + ", " + str(feature_vector(sqlContentVector, sentenceContentVector)) + ");"
        curs.execute(insert_query)
#        feature_sentence = str(sql_id) + '\t' + str(sentence_id) + '\t' + str(feature_alignment(sql_id, sqlContentWords, sentence_id, sentenceContentWords)) + '\t' + str(feature_distance(sql_pos, sentence_pos)) + '\t' +str(feature_vector(sqlContentVector, sentenceContentVector)) + '\n'

#        writeFile.write(feature_sentence)


    conn.commit()
    curs.close()
    conn.close()
        # print sql_id, '\t', sentence_id, '\t', feature_alignment(sql_id, sqlContentWords, sentence_id, sentenceContentWords), '\t', feature_distance(sql_pos, sentence_pos), '\t', feature_vector(sqlContentVector, sentenceContentVector)
