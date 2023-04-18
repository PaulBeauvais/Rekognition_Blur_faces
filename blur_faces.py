import os
import boto3
from tkinter.filedialog import askopenfilename, askdirectory
from tkinter.simpledialog import askfloat, askstring
from tkinter import *
from PIL import ImageDraw, ExifTags, ImageColor, ImageFilter, ImageOps, ImageStat
import PIL.Image
import glob

def clearConsole():
    command = 'clear'
    if os.name in ('nt', 'dos'):  # If Machine is running on Windows, use cls
        command = 'cls'
    os.system(command)


def askRunType():
    Tk().withdraw()
    message = 'Type S for single file or B to process all jpg files in a directory'
    while True:
        ask = askstring('single or batch process?', message)
        if ask == None:
            quit()
        ask = ask.lower()
        if ask != 'b' and ask != 's':
            message = 'Input must be "S" for single file process or "B" for Batch Process of directory'
        else:
            return ask


def getBlurRatio():
    Tk().withdraw()
    userPrompt = 'Please enter blur ratio between 10 and 90'
    while True:
        x = askfloat('Faces to blur (as percent of largest face)',userPrompt)
        if x == None:
            quit()
        elif x < 10 or x >99:
            userPrompt = 'Number must be between 10 and 90 please try again.'
        else:
            return x *.01


def getSingleFile():
    Tk().withdraw()
    openFile = askopenfilename(filetypes=[('Photos','*.jpg')], title="Select File to Blur")
    return openFile


def getTargetDirectory():
    Tk().withdraw()  # we don't want a full GUI, so keep the root window from appearing
    targetdirectory = ''

    while True:
        if targetdirectory == None:
            quit()
        elif os.path.isdir(targetdirectory) == False:
            targetdirectory =askdirectory(title="please select directory to place blurred files")
        elif os.path.isdir(targetdirectory) == True:
                return targetdirectory

def getSourceDirectory():
    Tk().withdraw()  # we don't want a full GUI, so keep the root window from appearing
    sourcedirectory = ''

    while True:
        if sourcedirectory == None:
            quit()
        elif os.path.isdir(sourcedirectory) == False:
            sourcedirectory =askdirectory(title="please select source directory to blur (all .jpg files)")
        elif os.path.isdir(sourcedirectory) == True:
                return sourcedirectory


def getSuffix():
    suffix = '_blurred'

    userInput = askstring(prompt="Please enter suffix for output file:", title="File Suffix")
    if userInput == None:
        quit()

    if userInput.strip() == '':
        userInput = suffix
    
    return userInput.strip()

def targetsavefilepath(sourcepath: str, suffix: str, targetdirectory: str = '') -> str:
    

    if targetdirectory == '':
        targetdirectory = os.path.dirname(sourcepath)

    return os.path.join(targetdirectory, os.path.splitext(os.path.basename(sourcepath))[0] + suffix + '.jpg')
     
    
    
def get_bounding_boxes(photo: str) -> dict:

    client=boto3.client('rekognition')

    ref_image = 'reference_image.jpg'
    with PIL.Image.open(photo) as img:
        grey_image = ImageOps.grayscale(img)
        grey_image.save(ref_image)

    with open(ref_image, 'rb') as img:       
        response = client.detect_faces(Image={'Bytes': img.read()}, Attributes=['ALL'])

    if os.path.exists(ref_image):
        os.remove(ref_image)

    return response['FaceDetails']


def blurfaces(photo: str, blur_area_threshold: float, savepath: str) -> str:

    # get bounding boxes from photo
    bounding_boxes = get_bounding_boxes(photo)

       # find largest area to blur (so we can blur on areas a certain percentage smaller than the largest)
    image = PIL.Image.open(photo)
    imgWidth, imgHeight = image.size

    biggest_blur_area = blur_area_threshold
    for faceDetail in bounding_boxes:
        box = faceDetail['BoundingBox']
        width = int(imgWidth * box['Width'])
        height = int(imgHeight * box['Height'])
        if int(width * height) > biggest_blur_area:
            biggest_blur_area = int(width * height)

    blur_area_threashold = biggest_blur_area * blur_area_threshold

    
 # calculate and display bounding boxes for each detected face
    if len(bounding_boxes) > 0:     
        print('Detected faces for ' + photo)    
        for faceDetail in bounding_boxes:
            print('The detected face is between ' + str(faceDetail['AgeRange']['Low']) 
                + ' and ' + str(faceDetail['AgeRange']['High']) + ' years old')
            
            box = faceDetail['BoundingBox']
            left = int(imgWidth * box['Left'])
            top = int(imgHeight * box['Top'])
            width = int(imgWidth * box['Width'])
            height = int(imgHeight * box['Height'])
            # print('-'* 80)
            # print("Blur Area: " + str(width*height))
            # print('Left: ' + '{0:.0f}'.format(left))
            # print('Top: ' + '{0:.0f}'.format(top))
            # print('Face Width: ' + "{0:.0f}".format(width))
            # print('Face Height: ' + "{0:.0f}".format(height))
            # print('-'* 80)

            if width * height <= blur_area_threashold:
                cropbox = (left,top, left + width, top + height)
                cropped_image = image.crop(cropbox)
                blurred_image = cropped_image.filter(ImageFilter.GaussianBlur(radius=20))
                image.paste(blurred_image,cropbox)
        image.save(savepath)
        return f'file saved as {savepath}'
    else:
        print('no faces detected')

        
        


if __name__ == "__main__":

    clearConsole()

    runmode = askRunType()
    print(f'Runmode = {runmode}')
    
    if runmode == 's' or runmode == 'b':
        blurratio = getBlurRatio()
        print(f'blurration = {blurratio}')

    if runmode == 's':
        pic = getSingleFile()
        print(f'file to blur = {pic}')
        
        filesuffix = getSuffix()
        print(f'Suffix to add to files = {filesuffix}')

        targetfile = targetsavefilepath(pic,filesuffix)
        print(f'Files to be saved as {targetfile}')

        blur = blurfaces(pic, blurratio, targetfile)
        print(blur)

    if runmode == 'b':
        batchfolder = getSourceDirectory()
        print(f'target directory = {batchfolder}')

        filesuffix = getSuffix()
        print(f'Suffix to add to files = {filesuffix}')

        targetdirectory = getTargetDirectory()
        print(f'files will be saved to {targetdirectory}')

        batchfiles = glob.glob(f'{batchfolder}/*.jpg')
        if len(batchfiles) > 0:
            for batchfile in batchfiles:
                targetfile = targetsavefilepath(batchfile, filesuffix, targetdirectory)
                blur = blurfaces(batchfile, blurratio, targetfile)
        else:
            print('No files to process - exiting')
            quit()



    

