import datetime


if __name__ == '__main__' :
    now = datetime.datetime.now()
    nowDate = list(map(int, str(now.date()).split('-')[1:]))
    nowTime = list(map(int, (str(now.time())[:8]).split(':')))
    nowRfidData = nowDate + nowTime
    print(nowRfidData)

