import pickle
from threading import Event
from time import time


JOBS_PICKLE = 'job_tuples.pickle'


def load_jobs(jq):
    now = time()

    with open(JOBS_PICKLE, 'rb') as fp:
        while True:
            try:
                next_t, job = pickle.load(fp)
            except EOFError:
                break  # Loaded all job tuples

            # Create threading primitives
            enabled = job._enabled
            removed = job._remove

            job._enabled = Event()
            job._remove = Event()

            if enabled:
                job._enabled.set()

            if removed:
                job._remove.set()

            next_t -= now  # Convert from absolute to relative time

            jq._put(job, next_t)


def save_jobs(jq):
    if jq:
        job_tuples = jq._queue.queue
    else:
        job_tuples = []

    with open(JOBS_PICKLE, 'wb') as fp:
        for next_t, job in job_tuples:
            skip = True
            # we only want to save the jobs which make sense to save
            # saving the edit jobs makes sense
            if job.name.startswith("edited"):
                skip = False
            # saving the manage jobs makes sense
            if job.name.startswith("managed"):
                skip = False
            # all the other jobs doesnt make sense, so lets skip those then
            if skip:
                continue
            # Back up objects
            _job_queue = job._job_queue
            _remove = job._remove
            _enabled = job._enabled

            # Replace un-pickleable threading primitives
            job._job_queue = None  # Will be reset in jq.put
            job._remove = job.removed  # Convert to boolean
            job._enabled = job.enabled  # Convert to boolean

            # Pickle the job
            pickle.dump((next_t, job), fp)

            # Restore objects
            job._job_queue = _job_queue
            job._remove = _remove
            job._enabled = _enabled


def save_jobs_job(context):
    save_jobs(context.job_queue)
