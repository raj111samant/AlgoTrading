try:
    from collections.abc import Hashable
except ImportError:
    from collections import Hashable
import datetime
import functools
import logging
import random
import re
import time

logger = logging.getLogger('schedule')

class ScheduleError(Exception):
    pass

class ScheduleValueError(ScheduleError):
    pass

class IntervalError(ScheduleValueError):
    pass

class CancelJob(object):
    pass

class Scheduler(object):
    def __init__(self):
        self.jobs = []

    def run_pending(self):
        runnable_jobs = (job for job in self.jobs if job.should_run)
        for job in sorted(runnable_jobs):
            self._run_job(job)

    def run_all(self, delay_seconds=0):
        logger.info('Running *all* %i jobs with %is delay inbetween',
                    len(self.jobs), delay_seconds)
        for job in self.jobs[:]:
            self._run_job(job)
            time.sleep(delay_seconds)

    def clear(self, tag=None):
        if tag is None:
            del self.jobs[:]
        else:
            self.jobs[:] = (job for job in self.jobs if tag not in job.tags)

    def cancel_job(self, job):
        try:
            self.jobs.remove(job)
        except ValueError:
            pass

    def every(self, interval=1):
        job = Job(interval, self)
        return job

    def _run_job(self, job):
        ret = job.run()
        if isinstance(ret, CancelJob) or ret is CancelJob:
            self.cancel_job(job)

    @property
    def next_run(self):
        if not self.jobs:
            return None
        return min(self.jobs).next_run

    @property
    def idle_seconds(self):
        return (self.next_run - datetime.datetime.now()).total_seconds()


class Job(object):
    def __init__(self, interval, scheduler=None):
        self.interval = interval  # pause interval * unit between runs
        self.latest = None  # upper limit to the interval
        self.job_func = None  # the job job_func to run
        self.unit = None  # time units, e.g. 'minutes', 'hours', ...
        self.at_time = None  # optional time at which this job runs
        self.last_run = None  # datetime of the last run
        self.next_run = None  # datetime of the next run
        self.period = None  # timedelta between runs, only valid for
        self.start_day = None  # Specific day of the week to start on
        self.tags = set()  # unique set of tags for the job
        self.scheduler = scheduler  # scheduler to register with

    def __lt__(self, other):
        return self.next_run < other.next_run

    def __str__(self):
        return (
            "Job(interval={}, "
            "unit={}, "
            "do={}, "
            "args={}, "
            "kwargs={})"
        ).format(self.interval,
                 self.unit,
                 self.job_func.__name__,
                 self.job_func.args,
                 self.job_func.keywords)

    def __repr__(self):
        def format_time(t):
            return t.strftime('%Y-%m-%d %H:%M:%S') if t else '[never]'

        def is_repr(j):
            return not isinstance(j, Job)

        timestats = '(last run: %s, next run: %s)' % (
                    format_time(self.last_run), format_time(self.next_run))

        if hasattr(self.job_func, '__name__'):
            job_func_name = self.job_func.__name__
        else:
            job_func_name = repr(self.job_func)
        args = [repr(x) if is_repr(x) else str(x) for x in self.job_func.args]
        kwargs = ['%s=%s' % (k, repr(v))
                  for k, v in self.job_func.keywords.items()]
        call_repr = job_func_name + '(' + ', '.join(args + kwargs) + ')'

        if self.at_time is not None:
            return 'Every %s %s at %s do %s %s' % (
                   self.interval,
                   self.unit[:-1] if self.interval == 1 else self.unit,
                   self.at_time, call_repr, timestats)
        else:
            fmt = (
                'Every %(interval)s ' +
                ('to %(latest)s ' if self.latest is not None else '') +
                '%(unit)s do %(call_repr)s %(timestats)s'
            )

            return fmt % dict(
                interval=self.interval,
                latest=self.latest,
                unit=(self.unit[:-1] if self.interval == 1 else self.unit),
                call_repr=call_repr,
                timestats=timestats
            )

    @property
    def second(self):
        if self.interval != 1:
            raise IntervalError('Use seconds instead of second')
        return self.seconds

    @property
    def seconds(self):
        self.unit = 'seconds'
        return self

    @property
    def minute(self):
        if self.interval != 1:
            raise IntervalError('Use minutes instead of minute')
        return self.minutes

    @property
    def minutes(self):
        self.unit = 'minutes'
        return self

    @property
    def hour(self):
        if self.interval != 1:
            raise IntervalError('Use hours instead of hour')
        return self.hours

    @property
    def hours(self):
        self.unit = 'hours'
        return self

    @property
    def day(self):
        if self.interval != 1:
            raise IntervalError('Use days instead of day')
        return self.days

    @property
    def days(self):
        self.unit = 'days'
        return self

    @property
    def week(self):
        if self.interval != 1:
            raise IntervalError('Use weeks instead of week')
        return self.weeks

    @property
    def weeks(self):
        self.unit = 'weeks'
        return self

    @property
    def monday(self):
        if self.interval != 1:
            raise IntervalError('Use mondays instead of monday')
        self.start_day = 'monday'
        return self.weeks

    @property
    def tuesday(self):
        if self.interval != 1:
            raise IntervalError('Use tuesdays instead of tuesday')
        self.start_day = 'tuesday'
        return self.weeks

    @property
    def wednesday(self):
        if self.interval != 1:
            raise IntervalError('Use wednesdays instead of wednesday')
        self.start_day = 'wednesday'
        return self.weeks

    @property
    def thursday(self):
        if self.interval != 1:
            raise IntervalError('Use thursdays instead of thursday')
        self.start_day = 'thursday'
        return self.weeks

    @property
    def friday(self):
        if self.interval != 1:
            raise IntervalError('Use fridays instead of friday')
        self.start_day = 'friday'
        return self.weeks

    @property
    def saturday(self):
        if self.interval != 1:
            raise IntervalError('Use saturdays instead of saturday')
        self.start_day = 'saturday'
        return self.weeks

    @property
    def sunday(self):
        if self.interval != 1:
            raise IntervalError('Use sundays instead of sunday')
        self.start_day = 'sunday'
        return self.weeks

    def tag(self, *tags):
        if not all(isinstance(tag, Hashable) for tag in tags):
            raise TypeError('Tags must be hashable')
        self.tags.update(tags)
        return self

    def at(self, time_str):
        if (self.unit not in ('days', 'hours', 'minutes') and not self.start_day):
            raise ScheduleValueError('Invalid unit')
        if not isinstance(time_str, str):
            raise TypeError('at() should be passed a string')
        if self.unit == 'days' or self.start_day:
            if not re.match(r'^([0-2]\d:)?[0-5]\d:[0-5]\d$', time_str):
                raise ScheduleValueError('Invalid time format')
        if self.unit == 'hours':
            if not re.match(r'^([0-5]\d)?:[0-5]\d$', time_str):
                raise ScheduleValueError(('Invalid time format for'
                                          ' an hourly job'))
        if self.unit == 'minutes':
            if not re.match(r'^:[0-5]\d$', time_str):
                raise ScheduleValueError(('Invalid time format for'
                                          ' a minutely job'))
        time_values = time_str.split(':')
        if len(time_values) == 3:
            hour, minute, second = time_values
        elif len(time_values) == 2 and self.unit == 'minutes':
            hour = 0
            minute = 0
            _, second = time_values
        else:
            hour, minute = time_values
            second = 0
        if self.unit == 'days' or self.start_day:
            hour = int(hour)
            if not (0 <= hour <= 23):
                raise ScheduleValueError('Invalid number of hours')
        elif self.unit == 'hours':
            hour = 0
        elif self.unit == 'minutes':
            hour = 0
            minute = 0
        minute = int(minute)
        second = int(second)
        self.at_time = datetime.time(hour, minute, second)
        return self

    def to(self, latest):
        self.latest = latest
        return self

    def do(self, job_func, *args, **kwargs):
        self.job_func = functools.partial(job_func, *args, **kwargs)
        try:
            functools.update_wrapper(self.job_func, job_func)
        except AttributeError:
            pass
        self._schedule_next_run()
        self.scheduler.jobs.append(self)
        return self

    @property
    def should_run(self):
        return datetime.datetime.now() >= self.next_run

    def run(self):
        logger.info('Running job %s', self)
        ret = self.job_func()
        self.last_run = datetime.datetime.now()
        self._schedule_next_run()
        return ret

    def _schedule_next_run(self):
        if self.unit not in ('seconds', 'minutes', 'hours', 'days', 'weeks'):
            raise ScheduleValueError('Invalid unit')

        if self.latest is not None:
            if not (self.latest >= self.interval):
                raise ScheduleError('`latest` is greater than `interval`')
            interval = random.randint(self.interval, self.latest)
        else:
            interval = self.interval

        self.period = datetime.timedelta(**{self.unit: interval})
        self.next_run = datetime.datetime.now() + self.period
        if self.start_day is not None:
            if self.unit != 'weeks':
                raise ScheduleValueError('`unit` should be \'weeks\'')
            weekdays = (
                'monday',
                'tuesday',
                'wednesday',
                'thursday',
                'friday',
                'saturday',
                'sunday'
            )
            if self.start_day not in weekdays:
                raise ScheduleValueError('Invalid start day')
            weekday = weekdays.index(self.start_day)
            days_ahead = weekday - self.next_run.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            self.next_run += datetime.timedelta(days_ahead) - self.period
        if self.at_time is not None:
            if (self.unit not in ('days', 'hours', 'minutes')
                    and self.start_day is None):
                raise ScheduleValueError(('Invalid unit without'
                                          ' specifying start day'))
            kwargs = {
                'second': self.at_time.second,
                'microsecond': 0
            }
            if self.unit == 'days' or self.start_day is not None:
                kwargs['hour'] = self.at_time.hour
            if self.unit in ['days', 'hours'] or self.start_day is not None:
                kwargs['minute'] = self.at_time.minute
            self.next_run = self.next_run.replace(**kwargs)
            if not self.last_run:
                now = datetime.datetime.now()
                if (self.unit == 'days' and self.at_time > now.time() and self.interval == 1):
                    self.next_run = self.next_run - datetime.timedelta(days=1)
                elif self.unit == 'hours' and self.at_time.minute > now.minute or (self.at_time.minute == now.minute and self.at_time.second > now.second):
                    self.next_run = self.next_run - datetime.timedelta(hours=1)
                elif self.unit == 'minutes' and self.at_time.second > now.second:
                    self.next_run = self.next_run - datetime.timedelta(minutes=1)
        if self.start_day is not None and self.at_time is not None:
            if (self.next_run - datetime.datetime.now()).days >= 7:
                self.next_run -= self.period

default_scheduler = Scheduler()
jobs = default_scheduler.jobs  # todo: should this be a copy, e.g. jobs()?

def every(interval=1):
    return default_scheduler.every(interval)

def run_pending():
    default_scheduler.run_pending()

def run_all(delay_seconds=0):
    default_scheduler.run_all(delay_seconds=delay_seconds)

def clear(tag=None):
    default_scheduler.clear(tag)

def cancel_job(job):
    default_scheduler.cancel_job(job)

def next_run():
    return default_scheduler.next_run

def idle_seconds():
    return default_scheduler.idle_seconds