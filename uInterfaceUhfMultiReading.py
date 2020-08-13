# coding: utf-8
#-*- coding:utf-8 -*-
import sys
from PyQt5 import QtWidgets, QtGui, uic
from PyQt5 import QtCore as core
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QMessageBox
from pymodbus.client.sync import ModbusTcpClient

import time, datetime, threading, os
from time import gmtime, strftime
import pandas as pd
import numpy as np

class Form(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = uic.loadUi("uInterfaceUhfMultiReading.ui", self)
        self.ui.show()
        initialButtonDisable(self, 'init')
        initialTableWideget(self.ui.tableWidget.horizontalHeader())
        global alarmClear
        global allTagEpcInfoTotal
        allTagEpcInfoTotal = []
        global iWriteEpcCount
        iWriteEpcCount = 1
        self.ui.pushButton_5.clicked.connect(self.stopBtn)

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
        t = MyThread(sampling_time, ip_address)

        try:
            t.daemon = True   # Daemon True is necessary
            t.start()
        except:
            self.ui.label.setText("Thread Fail")
        else:
            self.ui.label.setText("Trying to Connect")
            initialButtonDisable(self, 'connect')
            self.ui.label_14.setText(str(iWriteEpcCount))

    @pyqtSlot()
    def slot_2(self):
        global stop
        stop = True
        self.ui.label.setText("Disconnected")
        initialButtonDisable(self, 'init')

    @pyqtSlot()
    def slot_3(self):
        self.ui.label.setText("Searching")
        initialButtonDisable(self, 'searching')
        self.ui.tableWidget.setRowCount(0)
        global allTagEpcInfo, allTagEpcInfoBuffer, iterationTeaching, iterationMonitoring
        allTagEpcInfo, allTagEpcInfoBuffer = [[], []], [[], []]
        iterationTeaching, iterationMonitoring = 0, 0
        self.ui.label_8.setText(str(iterationTeaching)), self.ui.label_18.setText(str(iterationTeaching))
        global allTagEpcInfoTotal
        allTagEpcInfoTotal = []

    @pyqtSlot()
    def slot_4(self):
        self.ui.label.setText("Writing")
        initialButtonDisable(self, 'writing')

    @pyqtSlot()
    def slot_5(self):
        self.ui.label.setText("Monitoring")
        initialButtonDisable(self, 'monitoring')

    @pyqtSlot()
    def slot_6(self): #Pouse Condition
        if self.ui.pushButton_6.isChecked() :
            print(self.ui.pushButton_6.isChecked())
        else :
            print(self.ui.pushButton_6.isChecked())

    @pyqtSlot()
    def slot_7(self):
        alarmClear = True
        print("Alarm Clear", alarmClear)

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
        w.ui.tableWidget.setRowCount(0)
        teachingCountFlag = [False, False]
        rfidAntennaConnectedStatus = [False, False]

        while True:
            # sleep 'n'second before next polling
            time_interval = int(self.sampling_time)/1000
            time.sleep(time_interval)
            if stop == True:
                print("Communication Disconnected!")
                connection.close()
                break

            if w.ui.pushButton_7.isChecked() :
                w.ui.label.setText("Stop")
                w.ui.pushButton_7.setChecked(False)
                w.ui.pushButton.setDisabled(False)

            if not connection.connect():
                errString = "Connection Error, Check Your Input Information"
                print(errString)
                print(self.ip_address)
                w.ui.label.setText(errString)
                break
            else:
                if rTrigTeachingBtn :
                    rTrigTeachingBtn = False
                    w.ui.label.setText("Connected")
                    w.ui.pushButton.setDisabled(False)
                try:
                    input_buffer_regs = [connection.read_input_registers(0, 76).registers,\
                     connection.read_input_registers(76, 76).registers]
                except:
                    print("Error occur while communication.")
                else:
                    rfidChannelInput_dict = [rfidChannelInput(input_buffer_regs[0]), rfidChannelInput(input_buffer_regs[1])]
                    # Operating mode 0xB000 0xB012 check and setting to UHF Extended mode

                    if rfidAntennaConnectedStatus[0] != rfidChannelInput_dict[0]["notConnected"] \
                        or rfidAntennaConnectedStatus[1] != rfidChannelInput_dict[1]["notConnected"] :
                        rfidAntennaConnected(rfidChannelInput_dict[0]["notConnected"], rfidChannelInput_dict[1]["notConnected"])
                        rfidAntennaConnectedStatus[0] = rfidChannelInput_dict[0]["notConnected"]
                        rfidAntennaConnectedStatus[1] = rfidChannelInput_dict[1]["notConnected"]

                    anotherChannel = 1 if channel == 0 else 0

                    if not(w.ui.pushButton_6.isChecked()) :
                        if w.ui.label.text() == 'Searching' :
                            caseStep = 0 if caseStep > 10 else caseStep

                            if caseStep == 0 :
                                if rfidChannelInput_dict[channel]["responseCode"] == 0x0000 :
                                    connection.write_registers(rfidChannelModbus[channel], rfidCommand('inventory', settingCmdbuffer_dict))
                                    print("Inventory start")

                                    w.ui.label_19.setText("Inventory")
                                    caseStep = 1
                                else :
                                    w.ui.label_19.setText("Reset")
                                    connection.write_registers(rfidChannelModbus[channel], rfidCommand('reset', settingCmdbuffer_dict))
                                    print("Ready to idle")

                            if caseStep == 1 :
                                if rfidChannelInput_dict[channel]["responseCode"] == 0x8001:
                                    w.ui.label_19.setText("Inventory Busy")
                                    time.sleep(0.1)
                                elif rfidChannelInput_dict[channel]["responseCode"] == 0x0000:
                                    w.ui.label_19.setText("Idle")
                                    time.sleep(0.1)
                                else:
                                    if rfidChannelInput_dict[channel]["responseCode"] == 0x0001 :
                                        w.ui.label_19.setText("Inventory Done")

                                        print("rfidChannelInput_dict[channel]", rfidChannelInput_dict[channel])
                                        readFragmentNo = rfidChannelInput_dict[channel]["readFragmentNo"]
                                        inputBuffer = rfidChannelInput_dict[channel]["inputBuffer"]
                                        print("Inventory Successed!!")

                                        print("readFragmentNo", readFragmentNo)
                                        if readFragmentNo > 0 :
                                            inputBufferAll.append(inputBuffer)
                                            settingCmdbuffer_dict["readFragmentNo"] = readFragmentNo
                                            connection.write_registers(rfidChannelModbus[channel], rfidCommand('inventory', settingCmdbuffer_dict))
                                        else :
                                            settingCmdbuffer_dict["readFragmentNo"] = 0
                                            inputBufferAll.append(inputBuffer)
                                            inputAll = (np.array(inputBufferAll)).flatten()
                                            tagDataLength, tagStartAddress, tagEndAddress, tagCount, previousTagNum = 0,0,0,0,0

                                            print("else")
                                            while True :
                                                tagDataLength = inputAll[previousTagNum]
                                                if tagDataLength != 0 :
                                                    tagStartAddress = previousTagNum + 2
                                                    tagEndAddress = tagStartAddress + tagDataLength
                                                    tagUnionNum = inputAll[tagStartAddress]
                                                    tagEpcNum = inputAll[tagStartAddress + 1]
                                                    tagEpcLength = tagStartAddress+12
                                                    if tagUnionNum == int(w.ui.lineEdit_9.text()) :
                                                        print("Uion Number : " + str(tagUnionNum) + ", Idenfication : " + str(tagEpcNum))
                                                        print("Tag EPC : " + str(inputAll[tagStartAddress:tagEpcLength]))
                                                        print(inputAll[tagStartAddress:tagEpcLength])
                                                        allTagEpcInfo[channel] = list(allTagEpcInfo[channel])
                                                        allTagEpcInfo[channel].append(inputAll[tagStartAddress:tagEpcLength])
                                                        print(inputAll[tagStartAddress:tagEndAddress])
                                                    else :
                                                        print("It is not inclduded in union number group")
                                                    previousTagNum = tagEndAddress
                                                else :
                                                    print(np.unique(allTagEpcInfo[channel]))
                                                    try:
                                                        allTagEpcInfo[channel] = np.unique(allTagEpcInfo[channel], axis=0)
                                                    except:
                                                        print('No Union Tag Number')
                                                    else:
                                                        print(allTagEpcInfo[channel])

                                                        if not(np.array_equal(allTagEpcInfo[channel], allTagEpcInfoBuffer[channel])):

                                                            allTagEpcInfoOld = np.array(allTagEpcInfoBuffer[channel])
                                                            allTagEpcInfoNew = np.array(allTagEpcInfo[channel])[:,1]
                                                            allTagEpcInfoAnother = np.array(allTagEpcInfoBuffer[anotherChannel])

                                                            newAppendTagEpcbtwAnother = np.setdiff1d(allTagEpcInfoNew, allTagEpcInfoAnother)
                                                            print("newAppendTagEpcbtwAnother")
                                                            print(newAppendTagEpcbtwAnother)
                                                            newAppendTagEpc = np.setdiff1d(newAppendTagEpcbtwAnother, allTagEpcInfoOld)
                                                            print("newAppendTagEpc")
                                                            print(newAppendTagEpc)

                                                            allTagEpcInfoBuffer[channel] = allTagEpcInfo[channel]
                                                            print("allTagEpcInfo")
                                                            print(allTagEpcInfo)

                                                            for newTag in range(len(newAppendTagEpc)):
                                                                rowCount = w.ui.tableWidget.rowCount()
                                                                w.ui.tableWidget.insertRow(rowCount)
                                                                w.ui.tableWidget.setItem(rowCount, 1, QtWidgets.QTableWidgetItem(str(newAppendTagEpc[newTag])))
                                                                allTagEpcInfoTotal.append(newAppendTagEpc[newTag])
                                                        break


                                            inputBufferAll = []
                                            connection.write_registers(rfidChannelModbus[channel], rfidCommand('idle', settingCmdbuffer_dict))
                                            caseStep = 0

                                    else:
                                        print("Inventory failed!!")
                                        print("responseCode : " + str(rfidChannelInput_dict[channel]["responseCode"]))
                                        if channel == 0 :
                                            w.ui.label_19.setText("Inventory Fail")
                                        else :
                                            w.ui.label_20.setText("Inventory Fail")

                                        inputBufferAll = []
                                        connection.write_registers(rfidChannelModbus[channel], rfidCommand('idle', settingCmdbuffer_dict))
                                        caseStep = 0


                            elif caseStep == 2 :

                                isUniqueTag = False
                                if rfidChannelInput_dict[channel]["responseCode"] == 0x0000 :
                                    global iWriteEpcCount
                                    print(iWriteEpcCount)

                                    if firstNumList :
                                        byteListForWrite =[int(firstNumList[0]), int(w.ui.lineEdit_11.text()), iWriteEpcCount, 0]
                                    else:
                                        byteListForWrite =[int(w.ui.lineEdit_9.text()), int(w.ui.lineEdit_11.text()), iWriteEpcCount, 0]

                                    connection.write_registers(rfidOutputBufferModbus[channel], rfidOutputByteToWord(byteListForWrite))
                                    connection.write_registers(rfidChannelModbus[channel], rfidCommand('write', settingCmdbuffer_dict))
                                    print("write start")
                                    if channel == 0 :
                                        w.ui.label_19.setText("write")
                                    else :
                                        w.ui.label_20.setText("write")
                                    caseStep = 3
                                else :
                                    if channel == 0 :
                                        w.ui.label_19.setText("Reset")
                                    else :
                                        w.ui.label_20.setText("Reset")
                                    connection.write_registers(rfidChannelModbus[channel], rfidCommand('reset', settingCmdbuffer_dict))
                                    print("Ready to idle")

                            elif caseStep == 3 :
                                if rfidChannelInput_dict[channel]["responseCode"] == 0x8004:
                                    print("write Busy")
                                else:
                                    if rfidChannelInput_dict[channel]["responseCode"] == 0x0004:
                                        print("Write SCSS")
                                        if w.ui.checkBox_2.isChecked():
                                            iWriteEpcCount = iWriteEpcCount + 1
                                        w.ui.label_14.setText(str(iWriteEpcCount))
                                    else:
                                        print("Write Err")
                                    caseStep = 0
                                    # channel = 1 if channel == 0 else 0


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
    elif command == 'inventory' :
        settingCmdbuffer_dict["commandCode"] = 0x0001
        settingCmdbuffer_dict["startAddress"] = 1
    elif command == 'reset' :
        settingCmdbuffer_dict["commandCode"] = 0x8000
    elif command == 'readEpc' :
        settingCmdbuffer_dict["commandCode"] = 0x0002
        settingCmdbuffer_dict["startAddress"] = 0
        settingCmdbuffer_dict["MemoryArea"] = 0
    elif command == 'readLeak' :
        settingCmdbuffer_dict["commandCode"] = 0x0002
        settingCmdbuffer_dict["startAddress"] = 22
        settingCmdbuffer_dict["length"] = 2
        settingCmdbuffer_dict["MemoryArea"] = 0
        settingCmdbuffer_dict["lengthOfUidEpc"] = 2
    elif command == 'write' :
        settingCmdbuffer_dict["commandCode"] = 0x0004
        settingCmdbuffer_dict["startAddress"] = 0
        settingCmdbuffer_dict["length"] = 2
        settingCmdbuffer_dict["MemoryArea"] = 1
        settingCmdbuffer_dict["lengthOfUidEpc"] = 1


    settingCmdbuffer_dict["commandTimeout"] = int(w.ui.lineEdit_10.text())
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
        pre.ui.pushButton.setDisabled(True)
        pre.ui.pushButton_2.setDisabled(True)
        pre.ui.pushButton_3.setDisabled(False)
        pre.ui.pushButton_6.setDisabled(True)
        pre.ui.pushButton_7.setDisabled(True)
    elif mode =='connect':
        pre.ui.pushButton_3.setDisabled(True)
        pre.ui.pushButton_2.setDisabled(False)
        pre.ui.pushButton_6.setDisabled(False)
        pre.ui.pushButton_7.setDisabled(False)
    elif mode =='searching':
        pre.ui.pushButton.setDisabled(True)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = Form()
    sys.exit(app.exec_())
