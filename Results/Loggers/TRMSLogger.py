import mechanize
import os

class TrmsLogger(object):
    def __init__(self, config):
        self.host = config.url.PCDATA
        self.username = config.username.PCDATA
        self.password = config.password.PCDATA

    def resultsReady(self, resultLocation):
        browser = mechanize.Browser()
        loginPage = '%s/user/login/' % self.host
        browser.open(loginPage)
        form = browser.forms().next()
        form['username'] = self.username
        form['password'] = self.password
        browser.form = form
        browser.submit()

        if loginPage == browser.geturl():
            print 'TRMS Logger authentication failed!'
            return

        browser.open('%s/upload/batch/' % self.host)
        browser.select_form(predicate = lambda f: 'id' in f.attrs.keys()
            and f.attrs['id'] == 'upload_form')
        form = browser.form
        form['org'] = ['YouView']
        form['label'] = 'TASUpload'

        resultName = resultLocation.split(os.path.sep)[-1]
        form.add_file(open(resultLocation, 'r'),
            content_type = 'text/plain',
            filename = resultName,
            name = 'rp_zip')
        browser.form = form
        result = browser.submit()
        result = result.readlines()
        browser.close()

        if '<div>Success</div>' in result:
            print 'TRMS Logger : Success'
        else: print 'TRMS Logger : Failure'

    def shutdown(self): pass
