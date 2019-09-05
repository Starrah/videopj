import run_img_task
import run_multi_img_task
import multiprocessing

'''

list_of_tasks = 'autoencoder curvature denoise edge2d edge3d \
keypoint2d keypoint3d colorization jigsaw \
reshade rgb2depth rgb2mist rgb2sfnorm \
room_layout segment25d segment2d vanishing_point \
segmentsemantic class_1000 class_places inpainting_whole\
ego_motion \
fix_pose \
non_fixated_pose \
point_match'
list_of_tasks = list_of_tasks.split()

'''

def work(task, im_name, store_name, store_rep=False, store_pred=False, is_multi_task=False):
    '''

    :param task: task name
    :param im_name: input img path
        (eg: for single image: ./xxx/yyy/z.png)
        (eg: for multiple images: $IMG1,$IMG2,$IMG3)
    :param store_rep: The flag --store-rep enables saving the representation of the image prduced by task's encoder
    :param store_pred: To save the numerical prediction of the network
    :param store_name: name of stored file
    :param is_multi_task: if it will be a multiple-input-image task
    :return:

    '''
    if not is_multi_task:
        p = multiprocessing.Process(target=run_img_task.run_to_task,
                                    args=(task, im_name, store_rep, store_pred, store_name))
        p.start()
        print('task: ' + task + ' finished!')
    else:
        p = multiprocessing.Process(target=run_multi_img_task.run_to_task,
                                    args=(task, im_name, store_rep, store_pred, store_name))
        p.start()
        print('task: ' + task + ' finished!')

    return

if __name__=='__main__':
    work('rgb2sfnorm', 'assets/test.png', 'assets/test_sf.png')