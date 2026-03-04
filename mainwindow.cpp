#include "mainwindow.h"
#include "getCoverArtUtility.h"
#include "./ui_mainwindow.h"
#include <QFileDialog>
#include <QMimeData>
#include <QUrl>
#include <QPixmap>
#include <taglib/fileref.h>
#include <taglib/tag.h>
#include <taglib/audioproperties.h>
#include <taglib/mpegfile.h>
#include <taglib/id3v2tag.h>
#include <taglib/attachedpictureframe.h>
#include <QProcess>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    setAcceptDrops(true);

    ui->metadataTable->setHorizontalHeaderLabels({"Value"});
    ui->metadataTable->setVerticalHeaderLabels({"Title", "Artist", "Album", "Genre", "Track", "Year"});
}

MainWindow::~MainWindow()
{
    delete ui;
}

void MainWindow::dragEnterEvent(QDragEnterEvent *event)
{
    // check if dropped folder has a url (is a file)
    if (event->mimeData()->hasUrls())
    {
        event->acceptProposedAction();
    }
}

void MainWindow::dropEvent(QDropEvent *event)
{
    const QList<QUrl> urls = event->mimeData()->urls();
    if (urls.isEmpty())
        return;

    // Take the first dropped file
    QString filePath = urls.first().toLocalFile();

    if (!filePath.isEmpty()) {
        ui->fileInPathBox->setText(filePath);
        qDebug() << "Dropped file:" << filePath;
    }
}

void MainWindow::on_fileInBrowseButton_clicked()
{
    QString fileName = QFileDialog::getOpenFileName(
        this,
        "Open File",
        QDir::homePath(),              // starting directory
        "Music files (*.mp3 *.flac *.wav *.aac *.ogg *.m4a *.opus);;All files (*.*)"
    );

    ui->fileInPathBox->setText(fileName);
    ui->fileOutPathBox->setText(fileName);
}

void MainWindow::on_loadFileButton_clicked()
{
    QString fileName = ui->fileInPathBox->text();

    if (fileName.isEmpty())
        return;

    TagLib::FileRef f(fileName.toUtf8().constData());

    QPixmap cover = getCoverArtUtility(fileName);

    if (!cover.isNull()) {
        ui->coverArt->setPixmap(
            cover.scaled(
                ui->coverArt->size(),
                Qt::KeepAspectRatio,
                Qt::SmoothTransformation
                )
            );
    } else {
        ui->coverArt->clear();
        ui->coverArt->setText("No cover art");
    }

    if (!f.isNull() && f.tag()) {
        TagLib::Tag *tag = f.tag();

        QString title  = QString::fromStdString(tag->title().to8Bit(true));
        QString artist = QString::fromStdString(tag->artist().to8Bit(true));
        QString album  = QString::fromStdString(tag->album().to8Bit(true));
        QString genre  = QString::fromStdString(tag->genre().to8Bit(true));
        int year       = tag->year();
        int track      = tag->track();

        ui->metadataTable->setItem(0, 0, new QTableWidgetItem(title));
        ui->metadataTable->setItem(1, 0, new QTableWidgetItem(artist));
        ui->metadataTable->setItem(2, 0, new QTableWidgetItem(album));
        ui->metadataTable->setItem(3, 0, new QTableWidgetItem(genre));
        ui->metadataTable->setItem(4, 0, new QTableWidgetItem(QString::number(track)));
        ui->metadataTable->setItem(5, 0, new QTableWidgetItem(QString::number(year)));
    }

    if (f.audioProperties()) {
        TagLib::AudioProperties *props = f.audioProperties();
        qDebug() << "Length (s):" << props->length();
        qDebug() << "Bitrate:" << props->bitrate();
        qDebug() << "Sample rate:" << props->sampleRate();
    }

    qDebug() << "\n";
}

void MainWindow::on_tagButton_clicked()
{
    QString inPath  = ui->fileInPathBox->text();
    QString outPath = ui->fileOutPathBox->text();

    if (inPath.isEmpty() || outPath.isEmpty())
        return;

    QFileInfo inInfo(inPath);
    QFileInfo outInfo(outPath);

    QString workingPath = inPath;

    // ---- If output path differs, copy first ----
    if (inInfo.absoluteFilePath() != outInfo.absoluteFilePath()) {
        // Ensure target directory exists
        QDir().mkpath(outInfo.absolutePath());

        // Overwrite if destination already exists
        if (QFile::exists(outPath))
            QFile::remove(outPath);

        if (!QFile::copy(inPath, outPath)) {
            qDebug() << "Failed to copy file";
            return;
        }

        workingPath = outPath;
        qDebug() << "Created copy:" << outPath;
    } else {
        qDebug() << "Overwriting original file";
    }

    // ---- Open the file we are actually modifying ----
    TagLib::FileRef f(workingPath.toUtf8().constData());

    if (f.isNull() || !f.tag())
        return;

    TagLib::Tag* tag = f.tag();
    bool modified = false;

    QString newTitle  = ui->metadataTable->item(0, 0)->text();
    QString newArtist = ui->metadataTable->item(1, 0)->text();
    QString newAlbum  = ui->metadataTable->item(2, 0)->text();
    QString newGenre  = ui->metadataTable->item(3, 0)->text();
    QString newTrack  = ui->metadataTable->item(4, 0)->text();
    QString newYear   = ui->metadataTable->item(5, 0)->text();

    QPixmap newCoverArt = ui->coverArt->pixmap();

    if (!newTitle.isEmpty()) {
        tag->setTitle(TagLib::String(newTitle.toUtf8().constData(),
                                     TagLib::String::UTF8));
        modified = true;
    }

    if (!newArtist.isEmpty()) {
        tag->setArtist(TagLib::String(newArtist.toUtf8().constData(),
                                      TagLib::String::UTF8));
        modified = true;
    }

    if (!newAlbum.isEmpty()) {
        tag->setAlbum(TagLib::String(newAlbum.toUtf8().constData(),
                                     TagLib::String::UTF8));
        modified = true;
    }

    if (!newGenre.isEmpty()) {
        tag->setGenre(TagLib::String(newGenre.toUtf8().constData(),
                                     TagLib::String::UTF8));
        modified = true;
    }

    if (!newYear.isEmpty()) {
        bool ok;
        int year = newYear.toInt(&ok);
        if (ok) {
            tag->setYear(year);
            modified = true;
        }
    }

    if (!newTrack.isEmpty()) {
        bool ok;
        int track = newTrack.toInt(&ok);
        if (ok) {
            tag->setTrack(track);
            modified = true;
        }
    }

    if (!newCoverArt.isNull()) {

    }

    if (modified) {
        f.file()->save();
        qDebug() << "Metadata written to:" << workingPath;
    }
}

void MainWindow::on_fileOutBrowseButton_clicked()
{
    QString fileName = QFileDialog::getSaveFileName(
        this,
        "Save File",
        QDir::homePath(),              // starting directory
        "MP3 files (*.mp3);;FLAC files (*.flac);;WAV files (*.wav);;AAC files (*.aac);;OGG files (*.ogg);;M4A files (*.m4a);;OPUS files (*.opus);;All files (*.*)"
        );

    ui->fileOutPathBox->setText(fileName);
}


void MainWindow::on_artBrowseButton_clicked()
{
    QString fileName = QFileDialog::getOpenFileName(
        this,
        "Open File",
        QDir::homePath(),              // starting directory
        "Image files (*.jpg *.jpeg *.png *.bmp *.gif);;All files (*.*)"
        );

    QPixmap pixmap;
    if (pixmap.load(fileName)) {
        ui->coverArt->setPixmap(
            pixmap.scaled(
                ui->coverArt->size(),
                Qt::KeepAspectRatio,
                Qt::SmoothTransformation
                )
            );
    } else {
        qDebug() << "Failed to load image:" << fileName;
    }
}

void MainWindow::on_closeButton_clicked()
{
    close();
}


void MainWindow::on_grabButton_clicked()
{
    QString inputFile = ui->fileInPathBox->text().trimmed().remove("\n");
    if (inputFile.isEmpty())
        return;

    QStringList args;
    args << "songInfo.py" << inputFile;
    if (!ui->lastFMCheckBox->isChecked())
        args << "--no-lastfm";
    if (!ui->musicBrainzCheckBox->isChecked())
        args << "--no-musicbrainz";

    QProcess process;
    process.start("python3", args);
    process.waitForFinished();

    QString output = process.readAllStandardOutput();
    QString errors = process.readAllStandardError();

    qDebug() << "Output:\n" << output;
    if (!errors.isEmpty()) {
        qDebug() << "Errors:\n" << errors;
    }
}

