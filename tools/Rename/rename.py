# Naming convention of the images: {Name}_image_0  e.g. Ryan_image_43
# Use the start_index for assigning desired starter index naming, if assigned index range overlaps sequenced images, assign out of range first  then convert back

import os

if __name__ ==  '__main__':
#     file_path = input('Enter the path where the picture located: ') ## prompt user to input the path
    file_path = 'C:\\Users\\chienyu\\AIA\\final_project\\OpenLabeling\\images'
    os.chdir(file_path)
    
    pic_ls = [pic for pic in os.listdir()]

    # Enter the desired start index for the new naming
    start_index = 0
    
    for j, pic in enumerate(pic_ls, start_index):
        pic_name = 'Chien_image_{}.jpg'.format(j)
        os.rename(pic, pic_name)
        print('Rename picture {} to new name: {}'.format(pic, pic_name))

    print('finish rename!!')