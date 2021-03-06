const sleep2 = (timeountMS) => new Promise((resolve) => {
    setTimeout(resolve, timeountMS);
});


async function test_(isupgrade) {
    callback.init()
    await sleep2(100)
    callback.check_for_upgrade('https://baidu.com')
    await sleep2(100)
    callback.calculate_differences_for_upgrade()
    await sleep2(100)
    callback.whether_upgrade(isupgrade)
    await sleep2(100)

    if(isupgrade) {
        let old_files = [
            ['UpdaterHotupdatePackage.exe', true]
        ]
        let new_files = [
            ['2.6dev0', 35644, 'cc101a36a955aade313ea815e30234f557d622d2'],
            ['UpdaterHotupdatePackage.exe', 71218479, '8b321031c8b47f2bb6a273171d51b71b039b2579']
        ]
    
        callback.upgrading_old_files(old_files)
        callback.upgrading_new_files(new_files)
        await sleep2(100)
    
        callback.upgrading_before_downloading()
        await sleep2(100)
    
        // 开始下载
        for (const file of new_files) {
            let filename = file[0]
            let filelen = file[1]
            for(let i=0;i<11;i++) {
                let recv = i==0?0:parseInt(1/10*filelen)
                callback.upgrading_downloading(filename, recv, parseInt(i/10*filelen), filelen)
                await sleep2(30)
            }
        }
    
        callback.upgrading_before_installing()
    } else {
        callback.check_for_update('https://127.0.0.1.com')
        await sleep2(100)
        callback.calculate_differences_for_update()
        await sleep2(100)

        let old_files = [
            '.minecraft/mods/XNetGases-1.16.4-2.1.0 - 副本.jar',
            '.minecraft/mods/keng34343434.jar',
            '.minecraft/mods/updater-php - 快捷方式223123213.jar',
            '.minecraft/mods/vue-2.6.12343434.js',
        ]
        let new_files = [
            ['.minecraft/mods/ZeroCore2-1.16.4-2.0.+7.jar', 649672],
            ['.minecraft/mods/keng.jar', 36553],
            ['.minecraft/mods/updater-php - 快捷方式.jar', 543546],
            ['.minecraft/mods/vue-2.6.12.js', 37246],
        ]

        callback.updating_old_files(old_files)
        callback.updating_new_files(new_files)
        await sleep2(100)
        callback.updating_before_removing()

        for(let file of old_files)
            callback.updating_removing(file)

        await sleep2(100)
        callback.updating_before_downloading()

        for (const file of new_files) {
            let filename = file[0]
            let filelen = file[1]
            for(let i=0;i<11;i++) {
                let recv = i==0?0:parseInt(1/10*filelen)
                callback.updating_downloading(filename, recv, parseInt(i/10*filelen), filelen)
                await sleep2(30)
            }
        }

        await sleep2(100)
        callback.cleanup()
    }
}

function test(isupgrade) {
    test_(isupgrade)
}