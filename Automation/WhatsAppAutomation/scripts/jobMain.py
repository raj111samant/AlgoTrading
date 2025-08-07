import schedule
import time
import multiprocessing
import datetime
import WAAuto

RunningJobQueue = []

def PrintLog(*args):
    print(args)

def RunningJobWatchDog():
    PrintLog(datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"), "dog")
    for jobDetail in RunningJobQueue:
        p = jobDetail["process"]
        startTime = jobDetail["start"]
        duration = jobDetail["duration"]

        if p.is_alive() == False:
            RunningJobQueue.remove(jobDetail)
            PrintLog("Process complete {}".format(p.name), clear = False)
        else:
            if datetime.datetime.now() - startTime > duration:
                p.terminate()
                PrintLog("Process terminated {}".format(p.name), clear = False)
                RunningJobQueue.remove(jobDetail)
            else:
                PrintLog("Process running {}".format(p.name), clear = False)

def ScheduleAJob(jobDetails):
    PrintLog(datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"), "sche", jobDetails["function"].__name__)
    p = multiprocessing.Process(target=jobDetails["function"], name=jobDetails["function"].__name__)
    runningJobDetails = {"start": datetime.datetime.now(),
                        "duration": jobDetails["duration"],
                        "process": p}

    RunningJobQueue.append(runningJobDetails)
    p.start()

if __name__ == '__main__':
    schedule.every(60).seconds.do(RunningJobWatchDog)
    schedule.every().day.at("08:00").do(ScheduleAJob, WAAuto.RunSendParticipantListToAdminJob)

    while True:
        schedule.run_pending()
        time.sleep(15)