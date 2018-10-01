import os
from time import sleep
from flask import render_template, abort, request, send_file, flash, redirect, url_for
import psutil
from arm.ui import app, db
from arm.models.models import Job
from arm.config.config import cfg
from arm.ui.utils import convert_log, get_info, call_omdb_api
from arm.ui.forms import TitleSearchForm


@app.route('/logreader')
def logreader():

    logpath = cfg['LOGPATH']
    mode = request.args['mode']
    logfile = request.args['logfile']

    # Assemble full path
    fullpath = os.path.join(logpath, logfile)

    if mode == "armcat":
        def generate():
            f = open(fullpath)
            while True:
                new = f.readline()
                if new:
                    if "ARM:" in new:
                        yield new
                else:
                    sleep(1)
    elif mode == "full":
        def generate():
            with open(fullpath) as f:
                while True:
                    yield f.read()
                    sleep(1)
    elif mode == "download":
        clogfile = convert_log(logfile)
        return send_file(clogfile, as_attachment=True)
    else:
        # do nothing
        exit()

    return app.response_class(generate(), mimetype='text/plain')


@app.route('/activerips')
def rips():
    return render_template('activerips.html', jobs=Job.query.filter_by(status="active"))


@app.route('/titlesearch', methods=['GET', 'POST'])
def submitrip():
    job_id = request.args.get('job_id')
    job = Job.query.get(job_id)
    form = TitleSearchForm(obj=job)
    if form.validate_on_submit():
        form.populate_obj(job)
        flash('Search for {}, year={}'.format(form.title.data, form.year.data), category='success')
        # dvd_info = call_omdb_api(form.title.data, form.year.data)
        return redirect(url_for('list_titles', title=form.title.data, year=form.year.data, job_id=job_id))
        # return render_template('list_titles.html', results=dvd_info, job_id=job_id)
        # return redirect('/gettitle', title=form.title.data, year=form.year.data)
    return render_template('titlesearch.html', title='Update Title', form=form)


@app.route('/list_titles')
def list_titles():
    title = request.args.get('title')
    year = request.args.get('year')
    job_id = request.args.get('job_id')
    dvd_info = call_omdb_api(title, year)
    return render_template('list_titles.html', results=dvd_info, job_id=job_id)


# @app.route('/list_titles/<title>/<year>/<job_id>')
# def list_titles(title, year, job_id):
#     dvd_info = call_omdb_api(title, year)
#     return render_template('list_titles.html', results=dvd_info, job_id=job_id)


@app.route('/gettitle', methods=['GET', 'POST'])
def gettitle():
    imdbID = request.args.get('imdbID')
    job_id = request.args.get('job_id')
    dvd_info = call_omdb_api(None, None, imdbID, "full")
    return render_template('showtitle.html', results=dvd_info, job_id=job_id)


@app.route('/updatetitle', methods=['GET', 'POST'])
def updatetitle():
    new_title = request.args.get('title')
    new_year = request.args.get('year')
    job_id = request.args.get('job_id')
    job = Job.query.get(job_id)
    job.new_title = new_title
    job.new_year = new_year
    db.session.add(job)
    db.session.commit()
    flash('Title: {} ({}) was updated to {} ({})'.format(job.title, job.year, new_title, new_year), category='success')
    return redirect(url_for('home'))


@app.route('/logs')
def logs():
    mode = request.args['mode']
    logfile = request.args['logfile']

    return render_template('logview.html', file=logfile, mode=mode)


@app.route('/listlogs', defaults={'path': ''})
def listlogs(path):

    basepath = cfg['LOGPATH']
    fullpath = os.path.join(basepath, path)

    # Deal with bad data
    if not os.path.exists(fullpath):
        return abort(404)

    # Get all files in directory
    files = get_info(fullpath)
    return render_template('logfiles.html', files=files)


@app.route('/')
@app.route('/index.html')
def home():
    # freegb = getsize(cfg['RAWPATH'])
    freegb = psutil.disk_usage(cfg['ARMPATH']).free
    freegb = round(freegb/1073741824, 1)
    mfreegb = psutil.disk_usage(cfg['MEDIA_DIR']).free
    mfreegb = round(mfreegb/1073741824, 1)
    jobs = Job.query.filter_by(status="active")
    # for job in jobs:
    #     job.omdb_info = call_omdb_api(title=job.title, year=job.year)

    return render_template('index.html', freegb=freegb, mfreegb=mfreegb, jobs=jobs)
