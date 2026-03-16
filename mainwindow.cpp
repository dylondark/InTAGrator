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
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <taglib/mpegfile.h>
#include <taglib/id3v2tag.h>
#include <taglib/textidentificationframe.h>
#include <QString>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    setAcceptDrops(true);

    ui->metadataTable->setHorizontalHeaderLabels({"Tag", "Musicbrainz", "Last.fm", "Genius"});
    ui->metadataTable->setVerticalHeaderLabels({"Title", "Artist", "Album", "Release Date", "Genre", "Release Country", "Release Status", "MusicBrainz Track ID", "MusicBrainz Album ID", "Barcode", "ISRC", "Similar Artists", "Founding Date"});

    connect(&m_pythonProcess, &QProcess::readyReadStandardOutput, this, [this]() {
        ui->scriptLog->appendPlainText(QString::fromLocal8Bit(m_pythonProcess.readAllStandardOutput()));
    });

    connect(&m_pythonProcess, &QProcess::readyReadStandardError, this, [this]() {
        ui->scriptLog->appendPlainText(QString::fromLocal8Bit(m_pythonProcess.readAllStandardError()));
    });

    connect(&m_pythonProcess,
            QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this,
            &MainWindow::onPythonProcessFinished);
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

    ui->metadataTable->clearContents();
    ui->coverArt->clear();
    ui->coverArt->setPixmap(QPixmap(":/resources/defaultalbum.png"));

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
        ui->coverArt->setPixmap(QPixmap(":/resources/defaultalbum.png"));
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

    // Helper to get the first non-empty cell in a row across all columns
    auto getRowValue = [this](int row) -> QString {
        for (int col = 0; col < ui->metadataTable->columnCount(); ++col) {
            QTableWidgetItem *item = ui->metadataTable->item(row, col);
            if (item && !item->text().isEmpty()) {
                return item->text();
            }
        }
        return QString();
    };

    // Standard tags (writable to all formats)
    // Row 0: Title
    QString newTitle = getRowValue(0);
    if (!newTitle.isEmpty()) {
        tag->setTitle(TagLib::String(newTitle.toUtf8().constData(), TagLib::String::UTF8));
        modified = true;
    }

    // Row 1: Artist
    QString newArtist = getRowValue(1);
    if (!newArtist.isEmpty()) {
        tag->setArtist(TagLib::String(newArtist.toUtf8().constData(), TagLib::String::UTF8));
        modified = true;
    }

    // Row 2: Album
    QString newAlbum = getRowValue(2);
    if (!newAlbum.isEmpty()) {
        tag->setAlbum(TagLib::String(newAlbum.toUtf8().constData(), TagLib::String::UTF8));
        modified = true;
    }

    // Row 4: Genre
    QString newGenre = getRowValue(4);
    if (!newGenre.isEmpty()) {
        tag->setGenre(TagLib::String(newGenre.toUtf8().constData(), TagLib::String::UTF8));
        modified = true;
    }

    // Row 3: Release Date (extract year if possible)
    QString releaseDate = getRowValue(3);
    if (!releaseDate.isEmpty()) {
        bool ok;
        int year = releaseDate.left(4).toInt(&ok);
        if (ok && year > 0) {
            tag->setYear(year);
            modified = true;
        }
    }

    // For MP3 files, write extended ID3v2 tags
    TagLib::MPEG::File *mpegFile = dynamic_cast<TagLib::MPEG::File *>(f.file());
    if (mpegFile && mpegFile->ID3v2Tag()) {
        TagLib::ID3v2::Tag *id3v2 = mpegFile->ID3v2Tag();

        // Helper to add/update a TXXX (user-defined text) frame
        auto setUserTextFrame = [id3v2](const QString &description, const QString &value) {
            if (value.isEmpty())
                return;

            TagLib::String desc(description.toUtf8().constData(), TagLib::String::UTF8);
            TagLib::String val(value.toUtf8().constData(), TagLib::String::UTF8);

            // Remove existing frames with the same description
            auto frames = id3v2->frameList("TXXX");
            for (auto frame : frames) {
                auto *userFrame = dynamic_cast<TagLib::ID3v2::UserTextIdentificationFrame *>(frame);
                if (userFrame && userFrame->description() == desc) {
                    id3v2->removeFrame(frame);
                    break;
                }
            }

            // Create and add new frame
            TagLib::ID3v2::UserTextIdentificationFrame *frame =
                new TagLib::ID3v2::UserTextIdentificationFrame(TagLib::String::UTF8);
            frame->setDescription(desc);
            frame->setText(val);
            id3v2->addFrame(frame);
        };

        // Row 5: Release Country
        setUserTextFrame("RELEASE_COUNTRY", getRowValue(5));

        // Row 6: Release Status
        setUserTextFrame("RELEASE_STATUS", getRowValue(6));

        // Row 7: MusicBrainz Track ID
        setUserTextFrame("MUSICBRAINZ_TRACKID", getRowValue(7));

        // Row 8: MusicBrainz Album ID
        setUserTextFrame("MUSICBRAINZ_ALBUMID", getRowValue(8));

        // Row 9: Barcode
        setUserTextFrame("BARCODE", getRowValue(9));

        // Row 10: ISRC
        setUserTextFrame("ISRC", getRowValue(10));

        // Row 11: Similar Artists
        setUserTextFrame("SIMILAR_ARTISTS", getRowValue(11));

        // Row 12: Founding Date
        setUserTextFrame("FOUNDING_DATE", getRowValue(12));

        modified = true;
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

void MainWindow::on_grabButton_clicked()
{
    QString inputFile = ui->fileInPathBox->text().trimmed().remove("\n");
    if (inputFile.isEmpty())
        return;

    if (m_pythonProcess.state() != QProcess::NotRunning) {
        ui->scriptLog->appendPlainText(" A previous grab is still running. Please wait...");
        return;
    }

    ui->metadataTable->clearContents();
    ui->coverArt->clear();
    ui->coverArt->setPixmap(QPixmap(":/resources/defaultalbum.png"));

    m_lastGrabInputFile = inputFile;
    ui->scriptLog->clear();

    QStringList args;
    args << "songInfo.py" << inputFile;
    if (!ui->lastFMCheckBox->isChecked())
        args << "--no-lastfm";
    if (!ui->musicBrainzCheckBox->isChecked())
        args << "--no-musicbrainz";
    if (!ui->geniusCheckBox->isChecked())
        args << "--no-genius";
    if (!ui->lyricsCheckBox->isChecked())
        args << "--no-lyrics";
    if (!ui->coverArtCheckBox->isChecked())
        args << "--no-coverart";

    ui->progressBar->setEnabled(true);
    m_pythonProcess.start("python3", args);
    if (!m_pythonProcess.waitForStarted(3000)) {
        ui->progressBar->setEnabled(false);
        ui->scriptLog->appendPlainText("Failed to start python3 process");
    }
}

void MainWindow::onPythonProcessFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    ui->progressBar->setEnabled(false);

    // Capture any remaining output from the process
    QString stdoutText = QString::fromLocal8Bit(m_pythonProcess.readAllStandardOutput());
    if (!stdoutText.isEmpty())
        ui->scriptLog->appendPlainText(stdoutText);

    QString stderrText = QString::fromLocal8Bit(m_pythonProcess.readAllStandardError());
    if (!stderrText.isEmpty())
        ui->scriptLog->appendPlainText(stderrText);

    ui->scriptLog->appendPlainText(QStringLiteral("\nPython process finished (code %1, status %2)")
                                  .arg(exitCode)
                                  .arg(exitStatus == QProcess::NormalExit ? QStringLiteral("Normal") : QStringLiteral("Crash")));

    QString inputFile = m_lastGrabInputFile;
    if (inputFile.isEmpty())
        return;

    QString baseName = QFileInfo(inputFile).fileName();
    QString exeDir   = QCoreApplication::applicationDirPath();
    QString jsonPath = exeDir + "/" + baseName + "_metadata.json";

    QFile jsonFile(jsonPath);
    if (!jsonFile.open(QIODevice::ReadOnly)) {
        ui->scriptLog->appendPlainText("Failed to open JSON file: " + jsonPath);
        return;
    }

    QJsonDocument doc = QJsonDocument::fromJson(jsonFile.readAll());
    jsonFile.close();

    if (!doc.isObject()) {
        ui->scriptLog->appendPlainText("Invalid JSON");
        QFile::remove(jsonPath);
        return;
    }

    QJsonObject obj = doc.object();

    // AcoustID
    double score           = obj["score"].toDouble();
    QString recording_id   = obj["recording_id"].toString();
    QString title          = obj["title"].toString();
    QString artist         = obj["artist"].toString();

    // MusicBrainz
    QString mb_title       = obj["mb_title"].toString();
    QString mb_length_ms   = obj["mb_length_ms"].toString();
    QString album          = obj["album"].toString();
    QString release_date   = obj["release_date"].toString();
    QString track_number   = obj["track_number"].toString();
    QString label          = obj["label"].toString();

    auto toStringList = [&](const QString &key) {
        QStringList list;
        for (const QJsonValue &v : obj[key].toArray())
            list << v.toString();
        return list;
    };

    QStringList mb_tags     = toStringList("mb_tags");
    QStringList mb_genres   = toStringList("mb_genres");

    // Last.fm track
    QString lastfm_listeners = obj["lastfm_listeners"].toString();
    QString lastfm_playcount = obj["lastfm_playcount"].toString();
    QStringList lastfm_tags  = toStringList("lastfm_tags");
    QString lastfm_summary   = obj["lastfm_summary"].toString();
    QString duration_ms      = obj["duration_ms"].toString();

    // Last.fm artist
    QString artist_bio          = obj["artist_bio"].toString();
    QString artist_listeners    = obj["artist_listeners"].toString();
    QStringList artist_tags     = toStringList("artist_tags");
    QStringList similar_artists = toStringList("similar_artists");

    // Helper to convert arrays to comma-separated strings
    auto arrayToString = [&](const QString &key) -> QString {
        QStringList items = toStringList(key);
        return items.join(", ");
    };

    // Populate table rows based on row headers
    // Row 0: Title
    ui->metadataTable->setItem(0, 1, new QTableWidgetItem(mb_title));
    ui->metadataTable->setItem(0, 3, new QTableWidgetItem(obj["genius_title"].toString()));

    // Row 1: Artist
    ui->metadataTable->setItem(1, 1, new QTableWidgetItem(obj["mb_artist_credit"].toString()));
    ui->metadataTable->setItem(1, 3, new QTableWidgetItem(arrayToString("featured_artists")));

    // Row 2: Album
    ui->metadataTable->setItem(2, 1, new QTableWidgetItem(album));

    // Row 3: Release Date
    ui->metadataTable->setItem(3, 1, new QTableWidgetItem(release_date));
    ui->metadataTable->setItem(3, 3, new QTableWidgetItem(obj["genius_release_date"].toString()));

    // Row 4: Genre
    ui->metadataTable->setItem(4, 1, new QTableWidgetItem(arrayToString("mb_genres")));
    ui->metadataTable->setItem(4, 2, new QTableWidgetItem(arrayToString("lastfm_tags")));

    // Row 5: Release Country
    ui->metadataTable->setItem(5, 1, new QTableWidgetItem(obj["release_country"].toString()));

    // Row 6: Release Status
    ui->metadataTable->setItem(6, 1, new QTableWidgetItem(obj["release_status"].toString()));

    // Row 7: MusicBrainz Track ID
    ui->metadataTable->setItem(7, 1, new QTableWidgetItem(obj["recording_id"].toString()));

    // Row 8: MusicBrainz Album ID
    ui->metadataTable->setItem(8, 1, new QTableWidgetItem(obj["release_id"].toString()));

    // Row 9: Barcode
    ui->metadataTable->setItem(9, 1, new QTableWidgetItem(obj["release_barcode"].toString()));

    // Row 10: ISRC
    ui->metadataTable->setItem(10, 1, new QTableWidgetItem(arrayToString("mb_isrcs")));

    // Row 11: Similar Artists
    ui->metadataTable->setItem(11, 2, new QTableWidgetItem(arrayToString("similar_artists")));

    // Row 12: Founding Date (Career Begin)
    ui->metadataTable->setItem(12, 1, new QTableWidgetItem(obj["career_begin"].toString()));

    QPixmap pixmap = loadPixmapFromUrl(obj["cover_art_url"].toString());
    ui->coverArt->setPixmap(
        pixmap.scaled(
            ui->coverArt->size(),
            Qt::KeepAspectRatio,
            Qt::SmoothTransformation
            )
        );

    // Clean up the temp JSON file
    if (!ui->keepOutputCheckBox->isChecked())
        QFile::remove(jsonPath);

    ui->scriptLog->appendPlainText(QStringLiteral("%1 by %2 | score: %3").arg(title, artist).arg(score));
}

void MainWindow::on_keepButton_clicked()
{
    int rowCount = ui->metadataTable->rowCount();
    int colCount = ui->metadataTable->columnCount();

    for (int row = 0; row < rowCount; ++row) {
        for (int col = 1; col < colCount; ++col) {
            QTableWidgetItem *item = ui->metadataTable->item(row, col);
            if (item && !item->text().isEmpty()) {
                ui->metadataTable->setItem(row, 0, new QTableWidgetItem(item->text()));
                break;
            }
        }
    }
}


void MainWindow::on_clearButton_clicked()
{
    ui->metadataTable->clearContents();
    ui->coverArt->clear();
    ui->coverArt->setPixmap(QPixmap(":/resources/defaultalbum.png"));
}

