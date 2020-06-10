# coding: utf-8
#-*- coding:utf-8 -*-
import sys
from PyQt5 import QtWidgets, QtGui, uic
from PyQt5 import QtCore as core
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QMessageBox
from pymodbus.client.sync import ModbusTcpClient

import time, datetime, threading, os


class Form(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = uic.loadUi("uInterfaceAutoWrite_HF.ui", self)
        self.ui.show()

        global alarmClear
        global allTagEpcInfoTotal
        allTagEpcInfoTotal = []
        global iWriteEpcCount
        iWriteEpcCount = 1

    def stopBtn(self):
        global iWriteEpcCount
        iWriteEpcCount = int(self.ui.lineEdit_2.text())
        self.ui.label_14.setText(self.ui.lineEdit_2.text())
        print(iWriteEpcCount)

    @pyqtSlot()
    def slot_1(self):
        ip_address = self.ui.lineEdit.text()
        sampling_time = self.ui.lineEdit_3.text()

        global stop
        stop = False

        global stepReset
        stepReset = False

        t = MyThread(sampling_time, ip_address)

        try:
            t.daemon = True   # Daemon True is necessary
            t.start()
        except:
            self.ui.label.setText("Thread Fail")
        else:
            self.ui.label.setText("Trying to Connect")

    @pyqtSlot()
    def slot_2(self):
        global stop
        stop = True
        self.ui.label.setText("Disconnected")

    @pyqtSlot()
    def slot_3(self):
        self.ui.label.setText("Step Init")
        global stepReset
        stepReset = True

class MyThread(threading.Thread):
    def __init__(self, Sampling_time, ip_address):
        threading.Thread.__init__(self)
        self.sampling_time = Sampling_time
        self.ip_address = ip_address

    def run(self):
        SERVER_PORT = 502
        connection = ModbusTcpClient(host = self.ip_address, port = 502)
        folderDir = './log'
        makeDirectory(folderDir)         # 저장할 디렉토리 확인 후 없으면 생성
        progressBarNum = 0
        rTrigTeachingBtn = True
        inputBufferAll = []
        caseStep  = 0
        channel = 0
        rfidChannelModbus = [2048, 2124] # Output Setting Start Address
        rfidOutputBufferModbus = [2060, 2136]
        inventoryHeadInfo = []
        settingCmdbuffer_dict =  {"commandCode": 0, "loopCounter" : 0, "MemoryArea": 0, "startAddress": 0,
        "length" : 0, "lengthOfUidEpc" : 0, "headAddress" : 0, "commandTimeout" : 0,
        "readFragmentNo" : 0, "writeFragmentNo" : 0}
        teachingCountFlag = [False, False]
        rfidAntennaConnectedStatus = [False, False]
        tagPresentBuffer = "False"
        tagTrigger = "False"

        while True:
            # sleep 'n'second before next polling
            time_interval = int(self.sampling_time)/1000
            time.sleep(time_interval)
            if stop == True:
                w.ui.label.setText("Disconnected!")
                connection.close()
                break

            global stepReset
            if stepReset == True:
                caseStep = 0
                stepReset = False
                w.ui.label_11.setText('-')
                w.ui.label_14.setText('-')
                w.ui.label_16.setText('-')
                w.ui.label_20.setText('-')
                w.ui.lineEdit_2.setText('')
                w.ui.lineEdit_4.setText('')

            if not connection.connect():
                errString = "Connection Error, Check Your Input Information"
                print(errString)
                print(self.ip_address)
                w.ui.label.setText(errString)
                break
            else:
                try:
                    w.ui.label.setText("connected")
                    input_buffer_regs = [connection.read_input_registers(0, 76).registers,\
                     connection.read_input_registers(76, 76).registers]
                except:
                    print("Error occur while communication.")
                else:
                    rfidChannelInput_dict = [rfidChannelInput(input_buffer_regs[0]), rfidChannelInput(input_buffer_regs[1])]

                    tagPresent = rfidChannelInput_dict[0]["tagPresent"]
                    if tagPresent != tagPresentBuffer:
                        tagPresentBuffer = tagPresent
                        tagTrigger = "True"

                    if tagPresent == "True":
                        w.ui.label_21.setStyleSheet("color: green;" "background-color: #7FFFD4")
                    else:
                        w.ui.label_21.setStyleSheet("color: grey;" "border-style: solid")

                    # print(list(map(type,(tagPresent, tagPresentBuffer, tagTrigger))))



                    if caseStep == 0 :
                        w.ui.label_8.setText("write ready")
                        if rfidChannelInput_dict[channel]["responseCode"] == 0x0000 :
                            # TP 트리거 기능 삽입
                            if tagTrigger == "True" and tagPresent == "True":
                                now = datetime.datetime.now()
                                nowDate = list(map(int, str(now.date()).split('-')[1:]))
                                nowTime = list(map(int, (str(now.time())[:8]).split(':')))
                                nowRfidData = nowDate + nowTime
                                byteListForWrite = nowRfidData

                                connection.write_registers(rfidOutputBufferModbus[channel], rfidOutputByteToWord(byteListForWrite))
                                connection.write_registers(rfidChannelModbus[channel], rfidCommand('write', settingCmdbuffer_dict))
                                print("write start")
                                w.ui.label_19.setText("write start")
                                w.ui.lineEdit_2.setText(str(byteListForWrite))
                                w.ui.label_11.setText(str(datetime.datetime.now()))
                                caseStep = 1

                    if caseStep == 1 :
                        w.ui.label_8.setText("after write command")
                        if rfidChannelInput_dict[channel]["responseCode"] == 0x8004:
                            w.ui.label_19.setText("write Busy")
                            time.sleep(0.1)
                        elif rfidChannelInput_dict[channel]["responseCode"] == 0x0000:
                            w.ui.label_19.setText("idle")
                            time.sleep(0.1)
                        else:
                            if rfidChannelInput_dict[channel]["responseCode"] == 0x0004 :
                                w.ui.label_19.setText("Write Done")
                                w.ui.label_14.setText(str(datetime.datetime.now()))
                                caseStep = 2
                            else:
                                w.ui.label_19.setText("Write Error")
                                caseStep = 0

                            connection.write_registers(rfidChannelModbus[channel], rfidCommand('idle', settingCmdbuffer_dict))
                            time.sleep(0.1)

                    elif caseStep == 2 :
                        w.ui.label_8.setText("read ready")
                        if rfidChannelInput_dict[channel]["responseCode"] == 0x0000 :
                            connection.write_registers(rfidChannelModbus[channel], rfidCommand('read', settingCmdbuffer_dict))
                            w.ui.label_16.setText(str(datetime.datetime.now()))
                            time.sleep(0.1)
                            caseStep = 3
                        else :
                            w.ui.label_19.setText("Reset")
                            connection.write_registers(rfidChannelModbus[channel], rfidCommand('reset', settingCmdbuffer_dict))
                            print("Ready to idle")

                    elif caseStep == 3 :
                        w.ui.label_8.setText("after read command")
                        if rfidChannelInput_dict[channel]["responseCode"] == 0x8002:
                            w.ui.label_19.setText("read Busy")
                            time.sleep(0.1)
                        elif rfidChannelInput_dict[channel]["responseCode"] == 0x0000:
                            w.ui.label_19.setText("idle")
                            time.sleep(0.1)
                        else:
                            if rfidChannelInput_dict[channel]["responseCode"] == 0x0002 :
                                w.ui.label_20.setText(str(datetime.datetime.now()))
                                readData = rfidChannelInput_dict[channel]["inputBuffer"]
                                readDataInfo = str(readData[0:5])

                                w.ui.lineEdit_4.setText(readDataInfo)
                                w.ui.label_19.setText("read Done")
                                tagTrigger = False

                                with open('history.csv', 'a') as f:
                                    f.write(str(datetime.datetime.now()) + ',' + readDataInfo + '\n')

                                caseStep = 0
                            else:
                                w.ui.label_19.setText("Read Error")
                                caseStep = 2
                            connection.write_registers(rfidChannelModbus[channel], rfidCommand('idle', settingCmdbuffer_dict))
                            time.sleep(0.1)


def rfidAntennaConnected(bool1, bool2):
    if bool1 == "False":
        w.ui.label_12.setStyleSheet("color: green;" "background-color: #7FFFD4")
    else :
        w.ui.label_12.setStyleSheet("color: red;" "border-style: solid;" "border-width: 2px;"
                                    "border-color: #FA8072;" "border-radius: 3px")
    # if bool2 == "False":
    #     w.ui.label_13.setStyleSheet("color: green;" "background-color: #7FFFD4")
    # else :
    #     w.ui.label_13.setStyleSheet("color: red;" "border-style: solid;" "border-width: 2px;"
    #                                 "border-color: #FA8072;" "border-radius: 3px")


def makingOneDimentionZero(n):
    twoDimentionZero = [0]*n
    return twoDimentionZero

def makingTwoDimentionZero(n1, n2):
    twoDimentionZero = [[0]*n1, [0]*n2]
    return twoDimentionZero

def makingTwoDimentionList(n1, n2):
    twoDimentionList = [ [[]*n1 for x in range(n1)], [[]*n2 for x in range(n2)] ]
    return twoDimentionList

def rfidCommand(command, settingCmdbuffer_dict):
    if command == 'idle' :
        settingCmdbuffer_dict["commandCode"] = 0x0000
    elif command == 'write' :
        settingCmdbuffer_dict["commandCode"] = 0x0004
        settingCmdbuffer_dict["startAddress"] = 0
        settingCmdbuffer_dict["length"] = 100
    elif command == 'read' :
        settingCmdbuffer_dict["commandCode"] = 0x0002
        settingCmdbuffer_dict["startAddress"] = 0
        settingCmdbuffer_dict["length"] = 100


    rfidChannelOutput_dict = rfidChannelOutput(list(settingCmdbuffer_dict.values()))
    controlStatusList = list(rfidChannelOutput_dict.values())
    time.sleep(0.1)
    return controlStatusList

def rfidOutputByteToWord(byteList) :
    wordList = []
    byteListLength = len(byteList)
    if (byteListLength % 2 == 0): # 짝수
        for i in range(int(byteListLength/2)) :
            wordList.append(byteList[2*i] + byteList[2*i+1] * 256)
    else : # 홀수
        for i in range(int((byteListLength-1)/2)) :
            wordList.append(byteList[2*i] + byteList[2*i+1] * 256)
        wordList.append(byteList[byteListLength-1])
    return wordList

def rfidChannelOutput(settingCmdbuffer):
    commandCode = settingCmdbuffer[0]
    loopCounterMemoryArea = settingCmdbuffer[1] + settingCmdbuffer[2] * 256
    startAddressHigh = settingCmdbuffer[3]
    startAddressLow = 0
    length = settingCmdbuffer[4]
    lengthOfUidEpcHeadAddress = settingCmdbuffer[5] + settingCmdbuffer[6] * 256
    commandTimeout = settingCmdbuffer[7]
    readWriteFragmentNo = settingCmdbuffer[8] + settingCmdbuffer[9] * 256
    rfidChannelOutput_dict =  {"commandCode": commandCode, "loopCounterMemoryArea": loopCounterMemoryArea,
            "startAddressHigh": startAddressHigh, "startAddressLow": startAddressLow,
            "length" : length, "lengthOfUidEpcHeadAddress" : lengthOfUidEpcHeadAddress,
            "commandTimeout" : commandTimeout, "readWriteFragmentNo" : readWriteFragmentNo}
    return rfidChannelOutput_dict

def rfidChannelInput(register_buffer):
    responseCode = register_buffer[0]
    loopCount = register_buffer[1]
    register_buffer_2 = boolean_def(register_buffer[2])
    tagPresent = register_buffer_2[0]
    antennaDetuned = register_buffer_2[4]
    parameterNotSupported = register_buffer_2[5]
    errorReported = register_buffer_2[6]
    notConnected = register_buffer_2[7]
    hfHeadSwichedOn = register_buffer_2[8]
    continousModeActive = register_buffer_2[9]

    lengthRx = register_buffer[3]
    errorCode = register_buffer[4]
    tagCount = register_buffer[5]
    dataAvailable = register_buffer[6]
    register_buffer_7 = register_buffer[7].to_bytes(2, byteorder = 'big')
    readFragmentNo = register_buffer_7[1]
    writeFragmentNo = register_buffer_7[0]
    inputBufferWord = register_buffer[12:]

    inputBuffer =[]
    for i in range(len(inputBufferWord)):
        inputBufferWordToByte = inputBufferWord[i].to_bytes(2, byteorder = 'little')
        inputBuffer.append(inputBufferWordToByte[0])
        inputBuffer.append(inputBufferWordToByte[1])

    rfidChannelInput_dict = {"responseCode" : responseCode, "loopCount" : loopCount, "tagPresent" : tagPresent,
                            "antennaDetuned" : antennaDetuned, "parameterNotSupported" : parameterNotSupported,
                            "errorReported" : errorReported, "notConnected" : notConnected, "hfHeadSwichedOn" : hfHeadSwichedOn,
                            "continousModeActive" : continousModeActive, "length" : lengthRx,
                            "errorCode" : errorCode, "tagCount": tagCount, "dataAvailable": dataAvailable,
                            "readFragmentNo" : readFragmentNo, "writeFragmentNo" : writeFragmentNo, "inputBuffer" : inputBuffer}
    return rfidChannelInput_dict

def settingCmdbuffer_dict():
    return {"commandCode": 0, "loopCounter" : 0, "MemoryArea": 0, "startAddress": 0,
    "length" : 0, "lengthOfUidEpc" : 0, "headAddress" : 0, "commandTimeout" : 0,
    "readFragmentNo" : 0, "writeFragmentNo" : 0}

def makeDirectory(folderDir):
    if not os.path.isdir(folderDir):
        os.mkdir(folderDir)

def dataLogging(folderDir, register_buffer):
    logging_file_name = folderDir + '/' + str(datetime.datetime.today().strftime("%Y%m%d")) +'.txt'
    f = open(logging_file_name, mode='a', encoding='utf-8')
    str_read_list = str(register_buffer)[1:-1]
    now = datetime.datetime.now()
    cur_time = datetime.time(now.hour, now.minute, now.second)
    RF_logging = str(cur_time) + ', ' + str_read_list +'\n'
    f.write(RF_logging)
    f.close()

def listWidgetClear(clearNumber):
    if w.ui.listWidget.count() > clearNumber:
        w.ui.listWidget.clear()

def boolean_def(word):
    data = []
    b = 1
    for i in range(0, 16):
        if word & (b<<i) == 0:
            data.append("False")
        else:
            data.append("True")
    return data


def initialTableWideget(header):
    # header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)

    header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

def initialButtonDisable(pre, mode):
    print("initialButtonDisable")
    if mode == 'init':
        pre.ui.lineEdit.setDisabled(False)
        pre.ui.pushButton_2.setDisabled(True)
        pre.ui.pushButton_3.setDisabled(False)
    elif mode =='connect':
        pre.ui.pushButton_3.setDisabled(True)
        pre.ui.pushButton_2.setDisabled(False)
    elif mode =='searching':
        pre.ui.pushButton.setDisabled(True)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = Form()
    sys.exit(app.exec_())
