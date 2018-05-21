import requests
from requests.auth import HTTPBasicAuth
from io import BytesIO
from apscheduler.schedulers.background import BlockingScheduler

import logging
# Formatting logging
FORMAT = '%(asctime)s: %(message)s'
logging.basicConfig(format=FORMAT)

logger = logging.getLogger("capture_module")
logger.setLevel("INFO")

class CameraClient:
    """
    Can be used to interact with the camera over the network. 
    This has been especially designed to work with the Wanscam HW0029 camera.
    """
    
    SNAP_ENDPOINT = "/web/tmpfs/snap.jpg"
    WEB_PORT = 80

    def __init__(self, host, username="admin", password="admin"):
        """
        Creates a CameraClient which could be used to capture frame from the camera
        
        Arguments:
            host {str} -- The ip or hostname of the camera  
        
        Keyword Arguments:
            username {str} -- The username to use to connect (default: {"admin"})
            password {str} -- The password to use to connect (default: {"admin"})
        """
        self.host = host
        self.username = username

        self.password = password

        # Creating a basic authentification from the arguments
        self.auth = HTTPBasicAuth(self.username, self.password)

        # Defining the http request url which can be used to request an image to the camera
        self.url = "http://{}:{}{}".format(host, self.WEB_PORT, self.SNAP_ENDPOINT)

    def capture_raw(self): 
        """
        Could be used to get a single image from the camera. It is described by bytes.
        A skimage/opencv image (a simple [x, y, 3] numpy array) can be easily created with io.imread(camera.capture_raw()).
        
        Returns:
            BytesIO -- the byte stream describing the image

        Raises:
            RequestException -- if the connection was not succesfully completed, for ex. if the host can not be reached.
            BadCredentialsError -- if the credentials cannot be used to connect to the camera
            BadResponseFormat -- if womething went wrong with the camera response
        """
        # requesting the camera
        response = requests.get(self.url, auth=self.auth)

        # handling bad responses
        if response.status_code == 401: # bad credentials
            raise self.BadCredentialsError()
        elif not str(response.status_code).startswith("2"): # bad response code
            raise self.BadResponseFormat()

        # returning the image as a byte stream
        content = response.content
        response.close()
        return BytesIO(content)

    # ------- ERRORS ------- #
    class Error(Exception):
        pass

    class BadCredentialsError(Error):
        def __init__(self):
            super().__init__("The credentials cannot be used to connect to the camera")

    class BadResponseFormat(Error):
        def __init__(self):
            super().__init__("Something went wrong with the camera response")


class CameraCrawler:
    """
    Used to request the camera for a snap periodically. It handles connection loss.
    """

    def __init__(self, camera_client, handle_image_callback, hours = 0, minutes = 0, seconds = 0):
        """
        Creates an image crawler. It request for an image to the camera_client provided as an argument once every
        timelaps, which is defined by the hours, minutes and seconds parameters. For the crawler to start, use camera_crawler.start().
        For every image that has been received, the 'handle_image_callback(image_bytes_stream)' is called. The image_bytes_stream
        can be easily converted to an skimage/opencv images with image = io.imread(image_bytes_stream).
        
        Arguments:
            camera_client {CameraClient} -- The camera from which we want to retreive images
            handle_image_callback {Function} -- A function that has the following signature: func(image_bytes_stream)
        
        Keyword Arguments:
            hours {int} -- Hours between each request (default: {0})
            minutes {int} -- Minutes between each request (default: {0})
            seconds {int} -- Seconds between each request (default: {0})
        """

        self.camera_client = camera_client
        self.handle_image_callback = handle_image_callback

        # saving the base interval
        self.interval = (hours, minutes, seconds)

        # Creating a scheduler. It will ask for an image to the camera every timelaps provided as arguments
        self.scheduler = BlockingScheduler()
        self.job = self.scheduler.add_job(self.request_image, 'interval', hours = hours, minutes = minutes, seconds = seconds)

        # This is set to True when a connection error occured. 
        self.connection_error = False

    def request_image(self):
        """
        Used locally to request for an image to the camera. This is executed once every timelaps
        """

        try:
            image = self.camera_client.capture_raw()

            if self.connection_error == True:
                # There is no more error now, we can use the main interval
                logger.warning("The camera has been reconnected !")
                self.connection_error = False
                self.job.reschedule(trigger='interval', hours = self.interval[0], minutes = self.interval[1], seconds = self.interval[2])
            
            logger.info("Image fetched")

            self.handle_image_callback(image)
        except requests.RequestException :
            # Here, the camera could not be found
            # Retrying once every minute
            logger.error("Connection to camera lost, retrying in 1 minute")
            self.connection_error = True
            self.job.reschedule(trigger='interval', minutes = 1)
        except (CameraClient.BadCredentialsError, CameraClient.BadResponseFormat, Exception):
            logger.exception("An error has occured while retreiving the image")
            # Doing nothing, retrying the next time
           

    def start(self):
        """
        Starting capturing image from the camera
        """

        # we firstly get one image immediately
        self.request_image()

        # then, we start the scheduler
        self.scheduler.start()


if __name__ == "__main__":
    # here are some tests when not used as a module
    from skimage import io
    from skimage.viewer import ImageViewer

    camera = CameraClient("10.0.0.29")

    def handle_image(image_bytes_stream):
        # converting to a skimage/opencv image (simply a [x, y, 3] numpy array)
        image = io.imread(image_bytes_stream)

        ImageViewer(image).show()

    print("Creating crawler...")
    crawler = CameraCrawler(camera, handle_image, minutes=20)
    print("Starting crawler")
    crawler.start()
    
   